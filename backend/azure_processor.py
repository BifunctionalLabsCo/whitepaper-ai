# backend/azure_processor.py
import asyncio
import io
import re
import json
import os
from typing import Dict, List, Any, Optional
from fastapi import UploadFile
import PyPDF2
import uuid
import httpx
from dotenv import load_dotenv

load_dotenv()


class AzureWhitepaperProcessor:
    """Processor for analyzing whitepapers using Azure-hosted Llama model"""

    def __init__(self):
        self.azure_token = os.getenv("AZURE_AI_TOKEN")
        self.azure_endpoint = os.getenv("AZURE_AI_ENDPOINT")
        self.model_name = os.getenv("AZURE_AI_MODEL_NAME", "llama-3")

        if not self.azure_token or not self.azure_endpoint:
            raise ValueError(
                "Azure AI credentials not configured. Please set AZURE_AI_TOKEN and AZURE_AI_ENDPOINT"
            )

    async def extract_pdf_content(self, file: UploadFile) -> str:
        """Extract text content from PDF file"""
        try:
            print(f"Processing file: {file.filename}")
            file_content = await file.read()
            if not file_content:
                raise ValueError("File is empty")

            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_content))
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"

            if not text.strip():
                raise ValueError("No extractable text found. Image-based PDF?")

            return self._clean_text(text)

        except Exception as e:
            raise ValueError(f"Failed to process PDF: {str(e)}")

    def _clean_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\n\d+\n", "\n", text)
        text = re.sub(r"Page \d+", "", text)
        text = re.sub(
            r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
            "",
            text,
        )
        return text.strip()

    async def _call_azure_openai(
        self, messages: List[Dict[str, str]], max_tokens: int = 4000
    ) -> str:
        headers = {
            "Authorization": f"Bearer {self.azure_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": 0.3,
        }
        async with httpx.AsyncClient(timeout=180.0) as client:
            for attempt in range(5):
                try:
                    if attempt > 0:
                        await asyncio.sleep(2**attempt)
                    response = await client.post(
                        f"{self.azure_endpoint}/chat/completions", headers=headers, json=payload
                    )
                    if response.status_code == 401:
                        raise ValueError(
                            "401 Unauthorized: Invalid Azure AI token. Use 'github_pat_' token with AI access."
                        )
                    if response.status_code in [429, 503]:
                        await asyncio.sleep(min(60, (2**attempt) * 10))
                        continue
                    response.raise_for_status()
                    result = response.json()
                    if not result.get("choices"):
                        raise ValueError("Empty response from AI model.")
                    return result["choices"][0]["message"]["content"]
                except Exception as e:
                    if attempt == 4:
                        raise ValueError(f"Failed to call Azure AI: {str(e)}")
            raise ValueError("Max retries exceeded")

    def _extract_json(self, text: str) -> Any:
        """Extract the first valid JSON array or object from text."""
        stack = []
        start = None
        in_string = False
        escape = False
        for i, char in enumerate(text):
            if escape:
                escape = False
                continue
            if char == "\\":
                escape = True
                continue
            if char == '"' and not escape:
                in_string = not in_string
            if in_string:
                continue
            if char in ["{", "["]:
                if not stack:
                    start = i
                stack.append(char)
            elif char in ["}", "]"] and stack:
                opening = stack.pop()
                if not stack and start is not None:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        pass
        raise ValueError("No valid JSON object or array found in response")

    async def _generate_complete_course(
        self, text: str, title: Optional[str] = None
    ) -> Dict[str, Any]:
        analysis_text = text[:12000] if len(text) > 12000 else text
        prompt = f"""
        Create a comprehensive educational course from this whitepaper. Return valid JSON only.
        {{
            "title": "Course Title",
            "description": "2-3 sentence overview",
            "difficulty": "Intermediate",
            "objectives": ["Understand X", "Analyze Y", "Apply Z"],
            "modules": [
                {{
                    "id": "unique-id",
                    "title": "Module 1: Topic",
                    "content": "# Markdown\\n\\n## Key Points\\n...",
                    "estimatedTime": 900
                }}
            ]
        }}
        Requirements: 3-5 modules, 300-500 words each, markdown formatting, action verbs in objectives.
        """
        messages = [
            {"role": "system", "content": "Respond with valid JSON only."},
            {"role": "user", "content": prompt},
        ]
        response = await self._call_azure_openai(messages, max_tokens=6000)
        try:
            course_data = self._extract_json(response)
            for module in course_data.get("modules", []):
                module["id"] = str(uuid.uuid4())
                module["source_text"] = analysis_text
                module["flashcard"] = None
                module["quiz"] = None
                module.setdefault("completed", False)
                module.setdefault("timeSpent", 0)
            return course_data
        except Exception as e:
            print(f"JSON parse failed: {e}")
            return self._fallback_course(title, analysis_text)

    def _fallback_course(self, title: Optional[str], text: str) -> Dict[str, Any]:
        return {
            "title": title or "Whitepaper Course",
            "description": "Learn key concepts from this whitepaper.",
            "difficulty": "Intermediate",
            "objectives": ["Understand core concepts", "Analyze key findings"],
            "modules": [
                {
                    "id": str(uuid.uuid4()),
                    "title": "Introduction",
                    "content": "# Introduction\n\nOverview of the whitepaper.",
                    "source_text": text,
                    "flashcards": [],
                    "quiz": {"id": str(uuid.uuid4()), "questions": [], "attempts": 0},
                    "completed": False,
                    "timeSpent": 0,
                    "estimatedTime": 600,
                }
            ],
        }

    async def process_document(self, text: str, title: Optional[str] = None) -> Dict[str, Any]:
        print("Starting Azure AI analysis...")
        course_data = await self._generate_complete_course(text, title)
        return {
            "title": course_data.get("title", title or "Whitepaper Course"),
            "description": course_data.get("description", "Learn from this whitepaper"),
            "objectives": course_data.get("objectives", []),
            "modules": course_data.get("modules", []),
            "estimatedTime": sum(m.get("estimatedTime", 0) for m in course_data.get("modules", [])),
            "difficulty": course_data.get("difficulty", "Intermediate"),
            "createdAt": f"{asyncio.get_event_loop().time()}",
            "progress": 0,
        }

    async def generate_module_quiz(
        self, module_title: str, module_content: str, source_text: str
    ) -> Dict[str, Any]:
        await asyncio.sleep(3)
        num_questions = min(max(2, len(module_content.split()) // 300), 5)
        prompt = f"Create {num_questions} MCQs for: {module_title}. Content: {module_content[:1500]}. Respond with JSON."
        messages = [
            {"role": "system", "content": "Return JSON only."},
            {"role": "user", "content": prompt},
        ]
        try:
            response = await self._call_azure_openai(messages, max_tokens=1500)
            quiz_data = self._extract_json(response)
            for q in quiz_data.get("questions", []):
                q["id"] = str(uuid.uuid4())
            return {
                "id": str(uuid.uuid4()),
                "questions": quiz_data.get("questions", []),
                "attempts": 0,
                "generated_at": f"{asyncio.get_event_loop().time()}",
            }
        except Exception as e:
            print(f"Quiz gen failed: {e}")
            return {
                "id": str(uuid.uuid4()),
                "questions": [
                    {
                        "id": str(uuid.uuid4()),
                        "question": f"Main focus of {module_title}?",
                        "options": ["Key concepts", "Details", "Applications", "All"],
                        "correctAnswer": "All",
                        "explanation": "Covers multiple aspects.",
                    }
                ],
                "attempts": 0,
                "generated_at": f"{asyncio.get_event_loop().time()}",
            }

    async def generate_module_flashcards(
        self, module_title: str, module_content: str, source_text: str
    ) -> List[Dict[str, Any]]:
        await asyncio.sleep(3)
        num_flashcards = min(max(3, len(module_content.split()) // 200), 6)
        messages = [
            {
                "role": "system",
                "content": "Respond ONLY with a JSON array of objects. No commentary, no markdown.",
            },
            {
                "role": "user",
                "content": (
                    f"Generate exactly {num_flashcards} flashcards from the following text.\n"
                    f"Each flashcard must be a JSON object with the keys: 'question' and 'answer'.\n"
                    f"Return a single JSON array, like:\n"
                    f'[{{"question": "...", "answer": "..."}}, ...]\n\n'
                    f"Content:\n{module_content[:1200]}"
                ),
            },
        ]
        try:
            response = await self._call_azure_openai(messages, max_tokens=1000)
            cards = self._extract_json(response)
            print(f"\n\n{type(cards)}\n{cards}\n\n")
            for card in cards:
                card["id"] = str(uuid.uuid4())
                card["generated_at"] = f"{asyncio.get_event_loop().time()}"
            return cards
        except Exception as e:
            print(f"Flashcard gen failed: {e}")
            return [
                {
                    "id": str(uuid.uuid4()),
                    "front": f"Key concept from {module_title}",
                    "back": "Important information",
                    "difficulty": 1,
                    "generated_at": f"{asyncio.get_event_loop().time()}",
                }
            ]
