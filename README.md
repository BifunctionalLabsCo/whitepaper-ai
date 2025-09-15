# Whitepaper AI

"Turn any whitepaper into an interactive learning course in minutes."

## Overview

Whitepaper AI transforms complex technical whitepapers into structured, interactive learning experiences using Azure AI's Meta-Llama-3.1-405B-Instruct model. The platform analyzes academic and technical documents, breaks them into digestible learning modules, and generates interactive educational content including flashcards, quizzes, and progress tracking.

## Features

- **Whitepaper Ingestion**: Upload PDFs, URLs, or paste text directly
- **AI-Powered Content Structuring**: Automatic curriculum generation with 3-7 modules
- **Interactive Learning**: Flashcards, quizzes, and checkpoints with spaced repetition
- **Progress Tracking**: Visual dashboards, achievements, and cross-device sync
- **Export & Sharing**: PDF, PowerPoint, Notion templates, and collaborative features

## Tech Stack

### Frontend
- React 18 + Vite
- Tailwind CSS + Headless UI
- PDF.js for document preview
- React Context API for state management

### Backend
- FastAPI (Python)
- PyPDF2 + Tesseract OCR for document processing
- spaCy, NLTK for text processing
- ChromaDB for vector search
- Firebase Firestore for storage
- Firebase Auth for authentication

### AI Integration
- Azure AI Meta-Llama-3.1-405B-Instruct model
- Custom processing pipeline for educational content generation

## Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Azure AI credentials
- Firebase project (Auth + Firestore)

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd whitepaper-ai
```

2. Install frontend dependencies:
```bash
npm install
```

3. Install backend dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
# Create .env file in root directory
AZURE_AI_TOKEN="your_token_here"
AZURE_AI_ENDPOINT=https://models.inference.ai.azure.com/
AZURE_AI_MODEL_NAME=Meta-Llama-3.1-405B-Instruct
DEVELOPMENT=true
VITE_API_BASE_URL="http://localhost:8000/"
VITE_FIREBASE_API_KEY="your_firebase_key"
VITE_FIREBASE_AUTH_DOMAIN="whitepaper-ai-clone.firebaseapp.com"
VITE_FIREBASE_STORAGE_BUCKET="whitepaper-ai-clone.firebasestorage.app"
VITE_FIREBASE_MESSAGING_SENDER_ID="980420866394"
VITE_FIREBASE_APP_ID="1:980420866394:web:748ee34da4861f37e34363"
FIREBASE_CONFIG="whitepaper-ai-clone-firebase.creds.json"
# If deploying on Render, copy the full contents of your Firebase credentials JSON into an environment variable named FIREBASE_CONFIG (as a single line string)
```

5. Start the applications:
```bash
# Build frontend
npm run build

# Start backend server
uvicorn backend.main:app --reload
```

## Project Structure

```
whitepaper-ai/
├── backend/                              # FastAPI server
├── config.node.json                      # Node configuration
├── dist/                                 # Compiled frontend output
├── node_modules/                         # Node.js dependencies
├── src/                                  # React source code
├── vite.config.ts                        # Vite configuration
├── package.json                          # NPM package manifest
├── package-lock.json                     # NPM lock file
├── postcss.config.js                     # PostCSS config
├── tailwind.config.js                    # Tailwind CSS config
├── ts-config.json                        # TypeScript config
├── whitepaper-ai-clone-firebase.creds.json  # Firebase credentials
├── setup.sh                              # Setup script
└── README.md
```

## Deployment on Render

You can easily deploy this app on [Render](https://render.com/) using the following steps:

### 1. Backend (FastAPI)
- Create a new **Web Service** on Render.
- Set the environment to `Python 3.9`.
- Your FastAPI app should serve static files directly from the `dist/` directory.
- Use the following start command:
  ```
  uvicorn backend.main:app --host 0.0.0.0 --port 10000
  ```
- Add the necessary environment variables from your `.env` file to the Render dashboard.
- Ensure that `requirements.txt` is located in the **root** directory and use it to install dependencies.
- If your Firebase credentials are in a file, copy the **entire JSON content** and store it as the environment variable `FIREBASE_CONFIG`.

### 2. Frontend Deployment
- The React app is prebuilt and served by FastAPI from the `/dist` directory.
- Ensure your backend is configured to serve the static frontend by mounting the `dist/` directory (e.g., using `StaticFiles` in FastAPI).
- No separate static site deployment is necessary.

### Notes:
- Make sure CORS is properly configured in FastAPI for production.
- To enable proper routing, use [Render’s rewrite rules](https://render.com/docs/web-services#redirects-rewrites-and-retries) for single-page applications.

## License

MIT License
