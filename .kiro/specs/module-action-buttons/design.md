# Design Document

## Overview

The Module Action Buttons feature provides learners with one-click access to generate interactive learning materials for each course module. The system enables on-demand creation of quizzes and flashcards directly from module content, enhancing the learning experience without requiring upfront processing.

The feature integrates seamlessly with the existing module structure, adding two contextual action buttons that dynamically appear based on the current state of the module (whether quiz/flashcards have already been generated).

## Architecture

### High-Level Flow
1. **Module View** → Check if quiz/flashcards already exist
2. **Button Rendering** → Show/hide buttons based on module state
3. **User Action** → Click "Generate Quiz" or "Generate Flashcards"
4. **API Request** → Call corresponding backend endpoint
5. **Processing** → Show loading state while AI generates content
6. **Refresh** → Update UI with new content on success

### System Components
- **Action Button Service**: Manages button visibility and state
- **Quiz Generation API**: Endpoint for quiz creation
- **Flashcard Generation API**: Endpoint for flashcard creation
- **State Management**: Tracks generation status in UI
- **UI Components**: Button components with loading states

## Components and Interfaces

### Data Models

#### Module Actions Interface (Frontend)
```typescript
interface ModuleActionsState {
  isGeneratingQuiz: boolean
  isGeneratingFlashcards: boolean
  quizGenerated: boolean
  flashcardsGenerated: boolean
}
```

#### Extended Module Interface
```typescript
interface Module {
  // ... existing fields
  flashcards?: Flashcard[]
  quiz?: Quiz | null
}
```

#### Backend Response Models
```python
# Quiz generation response
{
  "id": "quiz-123",
  "questions": [
    {
      "id": "q-1",
      "question": "What is the main concept?",
      "options": ["A", "B", "C", "D"],
      "correctAnswer": "A",
      "explanation": "Detailed explanation..."
    }
  ],
  "attempts": 0
}

# Flashcard generation response
[
  {
    "id": "card-1",
    "front": "Key concept",
    "back": "Detailed explanation",
    "difficulty": 1
  }
]
```

### API Endpoints

#### Existing Endpoints (Enhanced)
```python
# Generate quiz for a module (already exists but needs UI integration)
@app.post("/api/courses/{course_id}/modules/{module_id}/generate-quiz")
async def generate_quiz(course_id: str, module_id: str)

# Generate flashcards for a module (already exists but needs UI integration)
@app.post("/api/courses/{course_id}/modules/{module_id}/generate-flashcards")
async def generate_flashcards(course_id: str, module_id: str)
```

### Frontend Components

#### ActionButtons Component
```typescript
interface ActionButtonsProps {
  module: Module
  courseId: string
  onRefresh: () => void
}

const ActionButtons: React.FC<ActionButtonsProps> = ({ module, courseId, onRefresh }) => {
  const [isGeneratingQuiz, setIsGeneratingQuiz] = useState(false)
  const [isGeneratingFlashcards, setIsGeneratingFlashcards] = useState(false)
  
  const handleGenerateQuiz = async () => {
    setIsGeneratingQuiz(true)
    try {
      await generateQuiz(courseId, module.id)
      toast.success('Quiz generated!')
      onRefresh()
    } catch (error) {
      toast.error('Failed to generate quiz. Please try again.')
    } finally {
      setIsGeneratingQuiz(false)
    }
  }

  const handleGenerateFlashcards = async () => {
    setIsGeneratingFlashcards(true)
    try {
      await generateFlashcards(courseId, module.id)
      toast.success('Flashcards generated!')
      onRefresh()
    } catch (error) {
      toast.error('Failed to generate flashcards. Please try again.')
    } finally {
      setIsGeneratingFlashcards(false)
    }
  }

  return (
    <div className="flex flex-col space-y-2">
      {!module.quiz && (
        <button
          onClick={handleGenerateQuiz}
          disabled={isGeneratingQuiz}
          className="btn-primary flex items-center justify-center"
        >
          <SparklesIcon className="h-5 w-5 mr-2" />
          {isGeneratingQuiz ? 'Generating...' : 'Generate Quiz'}
        </button>
      )}
      
      {!module.flashcards?.length && (
        <button
          onClick={handleGenerateFlashcards}
          disabled={isGeneratingFlashcards}
          className="btn-secondary flex items-center justify-center"
        >
          <SparklesIcon className="h-5 w-5 mr-2" />
          {isGeneratingFlashcards ? 'Generating...' : 'Generate Flashcards'}
        </button>
      )}
    </div>
  )
}
```

## Data Models

### Button Visibility Logic
- **Generate Quiz Button**: Visible when `module.quiz` is null or empty
- **Generate Flashcards Button**: Visible when `module.flashcards` is empty
- **Loading State**: Buttons show spinner while generation is in progress
- **Success State**: Buttons disappear and content appears automatically

### User Experience Flow
1. User views module without quiz/flashcards
2. Action buttons appear at appropriate location in UI
3. User clicks button → loading state begins
4. System calls backend API
5. On success: UI refreshes to show new content
6. On failure: Error toast appears, buttons remain visible

## Error Handling

### Generation Failures
- **Network Issues**: Show clear error message and retry option
- **AI Processing Errors**: Provide specific error details when possible
- **Content Issues**: Handle cases where module content is insufficient

### User Experience
- **Loading States**: Show spinner and disable button during processing
- **Success Feedback**: Toast notification on successful generation
- **Error Feedback**: Clear, actionable error messages
- **Retry Mechanism**: Buttons remain visible after failure for retry

### Monitoring and Logging
```python
# Log generation attempts
logger.info(f"Quiz generation requested", extra={
    "course_id": course_id,
    "module_id": module_id,
    "user_id": user_id
})

# Track generation success/failure
metrics.counter("quiz_generation.attempts", 1)
metrics.counter("quiz_generation.success", 1 if success else 0)
```

## Testing Strategy

### Unit Tests
- **Button Visibility**: Test button rendering based on module state
- **API Calls**: Mock API responses and test success/failure paths
- **State Management**: Verify loading states transition correctly
- **UI Updates**: Test UI refresh after successful generation

### Integration Tests
- **End-to-End Generation**: Test complete quiz/flashcard generation flow
- **API Integration**: Test communication between frontend and backend
- **State Persistence**: Verify generated content saves correctly
- **Error Scenarios**: Test handling of various failure conditions

### User Experience Testing
- **Loading States**: Verify proper display during generation
- **Success Flow**: Confirm content appears after generation
- **Error Handling**: Test user experience with failed generation
- **Multiple Attempts**: Test generating quiz/flashcards multiple times

### Test Data
- **Sample Modules**: Create test modules with varying content
- **Edge Cases**: Test with empty/very short module content
- **Error Scenarios**: Simulate API failures and timeouts
- **Performance Tests**: Test generation with large module content

## Security Considerations

### Rate Limiting
- Implement rate limiting on generation endpoints to prevent abuse
- Allow 3-5 generation attempts per module per hour

### User Authorization
- Verify user has access to the course and module before generation
- Prevent unauthorized quiz/flashcard generation

### Input Validation
- Validate module content before sending to AI processing
- Sanitize AI-generated content before display