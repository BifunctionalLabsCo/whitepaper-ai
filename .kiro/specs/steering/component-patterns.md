# Component Patterns

## Structure
- Each component in its own file
- Use TypeScript interfaces for props
- Destructure props at top
- No inline styles — use Tailwind classes

## Module Viewer Tabs
- Content / Flashcards / Quiz tabs
- Tab state local to `ModuleViewer`
- Use `prose` class for markdown rendering

## Button Styles
- `btn-primary`: solid blue, hover effect
- `btn-secondary`: outline, for secondary actions
- Loading states: show spinner, disable button

## Icon Usage
- Heroicons v2 (outline for regular, solid for active)
- GoogleIcon: custom SVG in `components/Icons/`

## Responsive Design
- Mobile-first layout
- Sidebar collapses on small screens
- Full-width cards on mobile

## File References
#[[file:frontend/src/components/ModuleViewer.tsx]]
#[[file:frontend/src/components/ProgressSidebar.tsx]]
#[[file:frontend/src/pages/CoursePage.tsx]]