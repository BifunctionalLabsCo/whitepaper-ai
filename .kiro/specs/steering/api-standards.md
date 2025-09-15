# API Standards

## REST Endpoints
- `/api/upload` → POST, returns `upload_id`
- `/api/design-course/{id}` → starts processing
- `/api/courses/{id}` → GET course data
- `/api/courses/{id}/modules/{id}/generate-quiz` → POST
- All responses JSON, errors use HTTP status codes

## Error Handling
- 401: Missing/invalid Firebase token
- 404: Course/upload not found
- 500: AI failed, PDF extraction error
- Always return `{ error: "message" }` for non-2xx

## Auth Flow
- All endpoints (except `/test-upload`) require `Authorization: Bearer <token>`
- Verify token via `firebase_admin.auth.verify_id_token()`
- Use `demo_user` only if disabled

## Request/Response Examples
POST `/api/courses/abc/modules/xyz/generate-quiz`
→ Returns quiz object with questions array

GET `/api/courses`
→ Returns list of user’s courses

## File References
#[[file:backend/main.py]]
#[[file:frontend/src/api/courses.ts]]