# backend/main.py
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import asyncio
import uuid
from typing import Dict, Any, Optional
import io

from dotenv import load_dotenv

from backend.azure_processor import AzureWhitepaperProcessor
from backend.models.course import Course, Module, ProcessingStatus
from backend.database import startup_db


load_dotenv()

app = FastAPI(title="Whitepaper AI API", version="1.0.0")

# Global database variable
db = None
processor = AzureWhitepaperProcessor()

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("VITE_API_BASE_URL")
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory status tracking (replace Redis later)
processing_status: Dict[str, ProcessingStatus] = {}


@app.on_event("startup")
async def startup_event():
    global db
    try:
        db = await startup_db()
        if db is None:
            raise RuntimeError("Failed to connect to database")
        print("✅ Database initialized successfully")
    except Exception as e:
        print(f"❌ DB init failed: {e}")
        raise


@app.post("/api/test-upload")
async def test_upload(file: UploadFile = File(...)):
    """Debug upload endpoint"""
    try:
        contents = await file.read()
        return {
            "filename": file.filename,
            "size": len(contents),
            "content_type": file.content_type,
            "status": "success"
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


@app.post("/api/upload")
async def upload_whitepaper(
    file: UploadFile = File(...),
    title: str = Form(None),
):
    """
    Upload a whitepaper PDF → store metadata in Firestore immediately.
    Background task will process it into a course.
    """
    upload_id = str(uuid.uuid4())
    user_id = "demo_user"  # Hardcoded for demo

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, 
            detail=f"Only PDF files are supported (received {file.content_type})"
        )

    # Read file content once
    file_content = await file.read()
    if len(file_content) == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    # Store raw PDF in Firestore
    upload_doc = {
        "id": upload_id,
        "user_id": user_id,
        "filename": file.filename,
        "title": title or file.filename.replace(".pdf", ""),
        "type": "pdf",
        "uploaded_at": asyncio.get_event_loop().time(),
        "status": "uploaded",
        "file_content": file_content  # CRITICAL: Store the actual file bytes
    }

    try:
        # Save metadata + file to Firestore
        await db.courses.insert_one(upload_doc)
    except Exception as e:
        print(f"❌ Firestore save error: {e}")
        raise HTTPException(status_code=500, detail="Failed to store upload metadata")

    # Set initial processing status
    processing_status[upload_id] = ProcessingStatus(
        id=upload_id,
        status="uploaded",
        progress=0,
        message="File uploaded. Ready to design course.",
    )

    return {"id": upload_id, "status": "uploaded", "message": "Upload successful!"}


@app.post("/api/design-course/{upload_id}")
async def design_course(upload_id: str):
    """Start designing the course from uploaded PDF"""
    # Fetch upload record
    upload_record = await db.courses.find_one({"id": upload_id})
    if not upload_record or upload_record.get("type") != "pdf":
        raise HTTPException(status_code=404, detail="Uploaded PDF not found")

    # Update status
    processing_status[upload_id] = ProcessingStatus(
        id=upload_id, status="processing", progress=10, message="Starting AI analysis..."
    )

    # Offload processing
    asyncio.create_task(process_pdf_background(upload_id))

    return {"id": upload_id, "status": "processing"}


async def process_pdf_background(upload_id: str):
    """Background task: Extract text → Generate course → Save modules & quiz placeholders"""
    try:
        print(f"🧠 Starting background processing for {upload_id}")

        # Get upload doc
        upload_doc = await db.courses.find_one({"id": upload_id})
        if not upload_doc:
            raise ValueError("Upload not found")

        # Get file content from Firestore
        file_content = upload_doc.get("file_content")
        if not file_content:
            raise ValueError("File content not found in database")

        # Create a file-like object from the stored bytes
        file_io = io.BytesIO(file_content)
        
        # Create a proper UploadFile object
        from fastapi import UploadFile as FastAPIUploadFile
        mock_file = FastAPIUploadFile(
            file=file_io,
            filename=upload_doc["filename"],
            content_type="application/pdf"
        )

        # Extract REAL text from the PDF (NO MORE SAMPLE TEXT!)
        processing_status[upload_id].message = "Extracting text from PDF..."
        processing_status[upload_id].progress = 20
        print("📄 Extracting text from PDF...")

        extracted_text = await processor.extract_pdf_content(mock_file)
        
        # Validate extracted text
        if not extracted_text or len(extracted_text.strip()) < 100:
            error_msg = "Extracted text is too short. The PDF may be image-based or corrupted."
            print(f"❌ {error_msg}")
            raise ValueError(error_msg)

        print(f"✅ Successfully extracted {len(extracted_text)} characters from PDF")

        processing_status[upload_id].progress = 30
        processing_status[upload_id].message = "Analyzing document structure..."

        # Use Azure AI to generate full course
        course_data = await processor.process_document(extracted_text, title=upload_doc["title"])

        # Assign new ID for course (different from upload_id if needed)
        course_id = str(uuid.uuid4())

        # Prepare modules
        module_docs = []
        module_ids = []

        for raw_module in course_data.get("modules", []):
            mod_id = raw_module["id"]
            module_ids.append(mod_id)

            full_module = Module(
                id=mod_id,
                course_id=course_id,
                title=raw_module["title"],
                content=raw_module["content"],
                source_text=raw_module["source_text"],
                estimatedTime=raw_module["estimatedTime"],
                flashcards=[],
                quiz={
                    "id": str(uuid.uuid4()),
                    "questions": [],
                    "attempts": 0,
                    "generated_at": asyncio.get_event_loop().time(),
                },
                completed=False,
                timeSpent=0,
            ).model_dump()

            module_docs.append(full_module)

        # Save all modules
        for mod in module_docs:
            await db.modules.insert_one(mod)

        # Create final course document
        final_course = Course(
            id=course_id,
            user_id="demo_user",
            title=course_data["title"],
            description=course_data["description"],
            objectives=course_data["objectives"],
            modules=module_ids,  # Only store IDs
            estimatedTime=course_data["estimatedTime"],
            difficulty=course_data["difficulty"],
            createdAt=course_data["createdAt"],
            progress=0,
        ).model_dump()

        # Save course
        await db.courses.insert_one(final_course)

        # Update status to completed
        processing_status[upload_id].status = "completed"
        processing_status[upload_id].progress = 100
        processing_status[upload_id].message = f"Course created! ID: {course_id}"
        processing_status[upload_id].course_id = course_id

        print(f"✅ Course generation complete: {course_id}")

        # Optional: Clean up temp upload entry
        # await db.courses.delete_one({"id": upload_id})

    except Exception as e:
        print(f"💥 Error in background processing: {e}")
        import traceback
        traceback.print_exc()
        
        error_msg = str(e)
        if "image-based" in error_msg or "scanned" in error_msg:
            user_msg = "PDF appears to be image-based. Text extraction failed."
        elif "Empty" in error_msg:
            user_msg = "Uploaded PDF is empty or corrupted."
        else:
            user_msg = f"Processing failed: {str(e)}"
        
        processing_status[upload_id].status = "failed"
        processing_status[upload_id].progress = 0
        processing_status[upload_id].message = user_msg
        print(f"❌ Processing failed: {user_msg}")


@app.get("/api/processing/{upload_id}")
async def get_processing_status(upload_id: str):
    """Get real-time status of course generation"""
    status = processing_status.get(upload_id)
    if not status:
        raise HTTPException(status_code=404, detail="Processing ID not found")
    return status


@app.get("/api/courses/{course_id}")
async def get_course(course_id: str):
    """Retrieve full course with expanded modules"""
    course = await db.courses.find_one({"id": course_id, "user_id": "demo_user"})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Expand modules
    expanded_modules = []
    for mod_id in course.get("modules", []):
        module = await db.modules.find_one({"id": mod_id})
        if module:
            # Inject flashcards/quiz if generated
            module.setdefault("flashcards", [])
            module.setdefault("quiz", {"questions": []})
            expanded_modules.append(module)

    course["modules"] = expanded_modules
    return course


@app.get("/api/courses")
async def get_user_courses():
    """List all courses for demo user"""
    courses = await db.courses.find({"user_id": "demo_user"}).to_list(100)
    # Filter only actual courses (not uploads) based on presence of 'objectives'
    return [c for c in courses if "objectives" in c]


# -----------------------------
# On-demand Content Generation
# -----------------------------


@app.post("/api/courses/{course_id}/modules/{module_id}/generate-quiz")
async def generate_quiz(course_id: str, module_id: str):
    module = await db.modules.find_one({"id": module_id})
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    try:
        quiz = await processor.generate_module_quiz(
            module["title"], module["content"], module.get("source_text", "")
        )

        await db.update_quiz(module_id, quiz)
        return quiz
    except Exception as e:
        print(f"❌ Quiz generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Quiz generation failed: {str(e)}")


@app.post("/api/courses/{course_id}/modules/{module_id}/generate-flashcards")
async def generate_flashcards(course_id: str, module_id: str):
    module = await db.modules.find_one({"id": module_id})
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")

    try:
        flashcards = await processor.generate_module_flashcards(
            module["title"], module["content"], module.get("source_text", "")
        )

        await db.update_flashcards(module_id, flashcards)
        return {"flashcards": flashcards}
    except Exception as e:
        print(f"❌ Flashcard generation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Flashcard generation failed: {str(e)}")


@app.post("/api/courses/{course_id}/modules/{module_id}/quiz")
async def submit_quiz(course_id: str, module_id: str, payload: dict):
    module = await db.modules.find_one({"id": module_id})
    if not module or "quiz" not in module:
        raise HTTPException(status_code=404, detail="Quiz not found")

    answers = payload.get("answers", {})
    correct = 0
    total = len(module["quiz"]["questions"])

    for q in module["quiz"]["questions"]:
        if answers.get(q["id"]) == q["correctAnswer"]:
            correct += 1

    score = (correct / total) * 100 if total > 0 else 0

    # Update attempt count and score in course
    await db.courses.update_one(
        {"id": course_id, "user_id": "demo_user", "modules.id": module_id},
        {"$inc": {"modules.$.quiz.attempts": 1}, "$set": {"modules.$.quiz.score": score}},
    )

    return {"score": score, "correct": correct, "total": total, "passed": score >= 70}


# -----------------------
# Export (Placeholder)
# -----------------------


@app.get("/api/courses/{course_id}/export/{format}")
async def export_course(course_id: str, format: str):
    if format not in ["pdf", "pptx", "notion"]:
        raise HTTPException(status_code=400, detail="Unsupported format")

    course = await db.courses.find_one({"id": course_id, "user_id": "demo_user"})
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    return {"message": f"Export to {format} will start shortly (mock)"}


# -----------------------
# Frontend Routing
# -----------------------

app.mount("/", StaticFiles(directory="./dist", html=True), name="frontend")


@app.get("/{full_path:path}")
async def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="API route not found")
    return FileResponse(os.path.join("./dist", "index.html"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
