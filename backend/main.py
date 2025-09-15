from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import asyncio
from typing import Optional, Dict, Any
import uuid

from backend.azure_processor import AzureWhitepaperProcessor
from backend.models.course import Course, ProcessingStatus, Module
from backend.database import startup_db

load_dotenv()

app = FastAPI(title="Whitepaper AI API", version="1.0.0")

# Global database variable, set on startup
db = None

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup event
@app.on_event("startup")
async def startup_event():
    try:
        db_instance = await startup_db()
        if db_instance is None:
            raise RuntimeError("DB returned None")
        global db
        db = db_instance
        print("✅ DB is ready for use")
    except Exception as e:
        print(f"❌ Failed to initialize DB: {e}")
        raise

# Global processor instance
processor = AzureWhitepaperProcessor()
print("✅ Azure WhitepaperProcessor initialized")

# In-memory storage for processing status (use Redis in production)
processing_status: Dict[str, ProcessingStatus] = {}


@app.post("/api/test-upload")
async def test_upload(file: UploadFile = File(...)):
    """Test endpoint for debugging file uploads"""
    try:
        content = await file.read()
        return {
            "filename": file.filename,
            "content_type": file.content_type,
            "size": len(content),
            "status": "success"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }

@app.post("/api/upload")
async def upload_whitepaper(
    type: str = Form(...),
    content: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None),
):
    """Upload a whitepaper without processing"""
    upload_id = str(uuid.uuid4())

    upload_data = {
        "id": upload_id,
        "type": type,
        "content": content,
        "title": title,
        "file_content": None,
        "user_id": "demo_user",  # Hardcoded for testing
        "uploaded_at": f"{asyncio.get_event_loop().time()}",
        "status": "uploaded"
    }

    if type == "pdf" and file:
        upload_data["file_content"] = await file.read()
        upload_data["filename"] = file.filename

    # Store in app state
    upload_storage = getattr(app.state, 'upload_storage', {})
    upload_storage[upload_id] = upload_data
    app.state.upload_storage = upload_storage

    processing_status[upload_id] = ProcessingStatus(
        id=upload_id,
        status="uploaded",
        progress=0,
        message="File uploaded successfully. Ready to design course."
    )

    return {"id": upload_id, "status": "uploaded", "message": "File uploaded successfully"}

@app.post("/api/design-course/{upload_id}")
async def design_course(upload_id: str):
    """Start course design process"""
    upload_storage = getattr(app.state, 'upload_storage', {})
    if upload_id not in upload_storage:
        raise HTTPException(status_code=404, detail="Upload not found")

    upload_data = upload_storage[upload_id]

    processing_status[upload_id].status = "processing"
    processing_status[upload_id].progress = 0
    processing_status[upload_id].message = "Starting course design..."

    asyncio.create_task(process_whitepaper_background(
        upload_id,
        upload_data["type"],
        upload_data["content"],
        upload_data["title"],
        upload_data["file_content"],
        upload_data["user_id"]
    ))

    return {"id": upload_id, "status": "processing"}

async def process_with_azure(text_content: str, title: Optional[str]) -> Dict[str, Any]:
    """Process document using Azure AI"""
    print("🤖 Processing with Azure AI...")
    course_data = await processor.process_document(text_content, title)
    print("✅ Azure AI processing successful!")
    return course_data

async def process_whitepaper_background(
    processing_id: str,
    upload_type: str,
    content: Optional[str],
    title: Optional[str],
    file_content: Optional[bytes],
    user_id: str = "demo_user"
):
    """Background task to process whitepaper"""
    try:
        print(f"Starting background processing for {processing_id}")
        print(f"Upload type: {upload_type}")
        print(f"Content length: {len(content) if content else 0}")
        print(f"File content length: {len(file_content) if file_content else 0}")

        processing_status[processing_id].message = "Extracting content..."
        processing_status[processing_id].progress = 10

        if upload_type == "pdf" and file_content:
            import io
            from fastapi import UploadFile

            class MockUploadFile:
                def __init__(self, content: bytes, filename: str = "document.pdf"):
                    self.content = content
                    self.filename = filename
                    self._file = io.BytesIO(content)
                
                async def read(self):
                    return self.content
                
                async def seek(self, position):
                    self._file.seek(position)
            
            mock_file = MockUploadFile(file_content)
            text_content = await processor.extract_pdf_content(mock_file)
            print(f"Extracted text length: {len(text_content)}")
        elif upload_type == "url" and content:
            text_content = await processor.extract_url_content(content)
        elif upload_type == "text" and content:
            text_content = content
        else:
            raise ValueError(f"Invalid upload type '{upload_type}' or missing content")

        if not text_content or len(text_content.strip()) < 100:
            raise ValueError("Extracted text is too short or empty")

        processing_status[processing_id].message = "Analyzing document structure..."
        processing_status[processing_id].progress = 30
        print("Starting AI analysis...")

        course_data = await process_with_azure(text_content, title)
        print("AI analysis completed successfully")

        processing_status[processing_id].message = "Generating interactive content..."
        processing_status[processing_id].progress = 70

        # Inject IDs into each module and insert into module collection
        modules = course_data.get("modules", [])
        for each in modules:
            each_mod = Module(**each, course_id=processing_id)
            await db.modules.insert_one(each_mod.model_dump())

        # Update modules pointers from in course document
        course_data["modules"] = [mod["id"] for mod in modules]

        course = Course(
            id=processing_id,
            user_id="demo_user",
            **course_data
        )
        await db.courses.insert_one(course.model_dump())
        print("Course and modules saved to database")

        processing_status[processing_id].status = "completed"
        processing_status[processing_id].progress = 100
        processing_status[processing_id].message = "Course ready!"
        print(f"Processing completed successfully for {processing_id}")

    except Exception as e:
        print(f"Error in background processing: {e}")
        import traceback
        traceback.print_exc()
        processing_status[processing_id].status = "failed"
        processing_status[processing_id].message = f"Processing failed: {str(e)}"

@app.get("/api/processing/{processing_id}")
async def get_processing_status(processing_id: str):
    """Get processing status"""
    if processing_id not in processing_status:
        raise HTTPException(status_code=404, detail="Processing ID not found")
    return processing_status[processing_id]

@app.get("/api/courses/{course_id}")
async def get_course(course_id: str):
    """Get course by ID (using demo_user)"""
    course = await db.courses.find_one({
        "id": course_id,
        "user_id": "demo_user"  # ← Match saved user ID
    })
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Expand module references if present
    if "modules" in course:
        module_ids = course["modules"]
        full_modules = []
        for mod_id in module_ids:
            module = await db.modules.find_one({"id": mod_id})
            if module:
                full_modules.append(module)
        course["modules"] = full_modules
    # print(f"\n\n{course}\n\n")

    return course

@app.get("/api/courses")
async def get_user_courses():
    """Get all courses for demo user"""
    courses = await db.courses.find({
        "user_id": "demo_user"  # ← Match saved user ID
    }).to_list(100)
    return courses

@app.post("/api/courses/{course_id}/modules/{module_id}/progress")
async def update_module_progress(
    course_id: str,
    module_id: str,
    progress_data: dict
):
    """Update module progress (demo_user)"""
    result = await db.courses.update_one(
        {
            "id": course_id,
            "user_id": "demo_user",
            "modules.id": module_id
        },
        {
            "$set": {
                "modules.$.completed": progress_data.get("completed", False),
                "modules.$.timeSpent": progress_data.get("timeSpent", 0)
            }
        }
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Course or module not found")
    return {"success": True}

@app.post("/api/courses/{course_id}/modules/{module_id}/generate-quiz")
async def generate_quiz(course_id: str, module_id: str):
    """Generate quiz for a specific module on-demand"""
    module = await db.modules.find_one({"id": module_id})
    # Now course["modules"] is a list of module IDs, not dicts.
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    try:
        quiz = await processor.generate_module_quiz(
            module["title"],
            module["content"],
            module.get("source_text", "")
        )

        await db.update_quiz(module_id, quiz)
        return quiz
    except Exception as e:
        print(f"Error generating quiz: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate quiz: {str(e)}")

@app.post("/api/courses/{course_id}/modules/{module_id}/generate-flashcards")
async def generate_flashcards(course_id: str, module_id: str):
    """Generate flashcards for a specific module on-demand"""
    module = await db.modules.find_one({"id": module_id})
    # Now course["modules"] is a list of module IDs, not dicts.
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    try:
        flashcards = await processor.generate_module_flashcards(
            module["title"],
            module["content"],
            module.get("source_text", "")
        )

        await db.update_flashcards(module_id, flashcards)
        return {"flashcards": flashcards}
    except Exception as e:
        print(f"Error generating flashcards: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate flashcards: {str(e)}")

@app.post("/api/courses/{course_id}/modules/{module_id}/quiz")
async def submit_quiz(
    course_id: str,
    module_id: str,
    quiz_data: dict
):
    """Submit quiz answers and get results (demo_user)"""
    module = await db.modules.find_one({"id": module_id})
    # Now course["modules"] is a list of module IDs, not dicts.
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    answers = quiz_data.get("answers", {})
    quiz = module["quiz"]
    correct_answers = sum(
        1 for q in quiz["questions"]
        if answers.get(q["id"]) == q["correctAnswer"]
    )
    total_questions = len(quiz["questions"])
    score = (correct_answers / total_questions) * 100 if total_questions > 0 else 0

    await db.courses.update_one(
        {
            "id": course_id,
            "user_id": "demo_user",
            "modules.id": module_id
        },
        {
            "$set": {"modules.$.quiz.score": score},
            "$inc": {"modules.$.quiz.attempts": 1}
        }
    )

    return {
        "score": score,
        "correct": correct_answers,
        "total": total_questions,
        "passed": score >= 70
    }

@app.get("/api/courses/{course_id}/export/{format}")
async def export_course(course_id: str, format: str):
    """Export course in specified format (demo_user)"""
    if format not in ["pdf", "pptx", "notion"]:
        raise HTTPException(status_code=400, detail="Invalid export format")

    course = await db.courses.find_one({
        "id": course_id,
        "user_id": "demo_user"
    })
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Placeholder for export logic
    # export_data = await processor.export_course(course, format)
    # return StreamingResponse(...)

    # For now, just return a placeholder
    return {"message": f"Export to {format} is not yet implemented"}

# Mount static files for frontend
app.mount("/", StaticFiles(directory="./dist", html=True), name="frontend")

@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    index_path = os.path.join("./dist", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Page not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)