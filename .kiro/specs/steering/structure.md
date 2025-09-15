# Project Structure

## Folder Layout
```
whitepaper-ai/
├── backend/
│   ├── azure_processor.py      # Main AI logic using Azure-hosted Llama
│   ├── database.py             # MongoDB connection & mock DB fallback
│   ├── main.py                 # FastAPI application entry point
│   ├── firebase_config.py      # Firebase Auth verification (optional)
│   └── models/                 # Pydantic-free course schema definitions
│       └── course.py           # Course/Module interface structure
│
├── frontend/
│   ├── public/                 # Static assets
│   └── src/
│       ├── api/                # API clients and request wrappers
│       │   ├── client.ts       # Axios instance with auth
│       │   └── courses.ts      # Course-related API calls
│       ├── components/         # Reusable UI components
│       │   ├── FlashcardSystem.tsx
│       │   ├── ModuleViewer.tsx
│       │   ├── Navbar.tsx
│       │   ├── ProgressSidebar.tsx
│       │   ├── QuizEngine.tsx
│       │   └── UploadComponent.tsx
│       ├── context/            # React Context providers
│       │   ├── AuthContext.tsx
│       │   └── LearningContext.tsx
│       ├── pages/              # Route-based views
│       │   ├── CoursePage.tsx
│       │   ├── DashboardPage.tsx
│       │   ├── HomePage.tsx
│       │   ├── LoginPage.tsx
│       │   └── UploadPage.tsx
│       ├── config/             # Configuration files
│       │   └── firebase.ts     # Firebase app initialization
│       ├── assets/             # Images, icons, etc.
│       ├── App.tsx             # Main router and layout
│       ├── main.tsx            # Entry point
│       └── index.css           # Global styles
│
├── .kiro/                      # Kiro-specific configuration
│   └── steering/               # Persistent project knowledge
│       ├── product.md          # Product vision and goals
│       ├── tech.md             # Tech stack overview
│       ├── structure.md        # This file
│       ├── api-standards.md    # REST conventions
│       ├── component-patterns.md # UI component rules
│       └── security-policies.md # Security guidelines
│
├── .env                        # Environment variables (local only)
├── .gitignore                  # Ignored files and patterns
├── package.json                # Frontend dependencies
├── requirements.txt            # Python backend dependencies
└── vite.config.ts              # Vite build configuration
```

## Naming Conventions
- **Files**: Use PascalCase for React components (`ModuleViewer.tsx`), kebab-case for configs (`vite.config.ts`)
- **Folders**: Lowercase, singular (`component`, not `components`)
- **Variables**: camelCase (TypeScript/JS), snake_case (Python)
- **Components**: `<Feature>Component.tsx` or `<Feature>.tsx` (e.g., `QuizEngine.tsx`)

## Import Patterns
- Frontend: Relative paths from `src/`, no aliases
- Backend: Direct imports within module
- Avoid circular dependencies between components

## Architectural Decisions
- **Frontend**: Component-per-feature, props drilling (no Redux/Zustand)
- **Backend**: Monolithic FastAPI app with minimal abstractions
- **AI Flow**: Upload → Extract Text → Prompt Azure AI → Save → Display
- **State Sync**: Manual refresh via `onRefresh()` callback (no WebSockets yet)
- **Auth**: Firebase ID token passed via `Authorization: Bearer <token>` header

## File References
#[[file:frontend/src/api/client.ts]]
#[[file:backend/main.py]]
#[[file:backend/azure_processor.py]]
#[[file:frontend/src/context/AuthContext.tsx]]
#[[file:frontend/src/components/ModuleViewer.tsx]]
```

### ✅ How to Use
1. Create `.kiro/steering/` in your project root
2. Paste this content into `structure.md`
3. Save and restart Kiro — it will now understand your full project layout

This ensures consistent code generation and seamless integration across frontend and backend.