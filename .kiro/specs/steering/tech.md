# Technology Stack

## Frontend
- **Framework**: React + Vite
- **Routing**: react-router-dom v6
- **State Management**: Context API (`AuthContext`, `LearningContext`)
- **Styling**: Tailwind CSS + Headless UI
- **UI Components**: Heroicons, Recharts, react-hot-toast
- **PDF Rendering**: pdfjs-dist (optional)
- **Forms**: Native inputs with validation

## Backend
- **Framework**: FastAPI (Python)
- **AI Model**: Azure-hosted Llama via GitHub PAT token
- **Database**: In-memory fallback → DynamoDB or MongoDB (planned)
- **Auth**: Firebase Authentication (ID token verification)
- **File Processing**: PyPDF2 for text extraction
- **HTTP Client**: httpx (async)

## Development Tools
- **IDE**: Kiro IDE (agent-steering, spec-to-code)
- **Type Safety**: TypeScript (frontend), Pydantic (backend – minimal use)
- **Environment**: .env + dotenv
- **Logging**: print() + console.log()

## Deployment Targets
- Frontend + Backend: Render
- Auth: Firebase
- Storage: Firestore

## Constraints
- Avoid heavy dependencies (no full Pydantic models)
- Use only essential packages
- Prefer direct API calls over ORMs