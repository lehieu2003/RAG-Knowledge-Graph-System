# RAG Knowledge Graph - Frontend

Modern React + TypeScript frontend for the RAG Knowledge Graph System.

## Features

- 💬 **Chat Interface**: Interactive Q&A with multiple retrieval modes
- 📄 **Document Management**: Upload and manage PDF documents
- 🔄 **Ingestion Monitoring**: Real-time pipeline status tracking
- 🕸️ **Knowledge Graph Explorer**: Search and browse entities

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Axios** for API calls
- **Lucide React** for icons
- **React Markdown** for message rendering

## Getting Started

### Install Dependencies

```bash
npm install
```

### Development Server

```bash
npm run dev
```

The app will be available at `http://localhost:3000`

### Build for Production

```bash
npm run build
```

### Preview Production Build

```bash
npm run preview
```

## Project Structure

```
src/
├── main.tsx              # Application entry point
├── App.tsx               # Main app component with routing
├── index.css             # Global styles with Tailwind
├── lib/
│   └── api.ts            # API client and types
├── components/
│   └── Layout.tsx        # Main layout with sidebar
└── pages/
    ├── ChatPage.tsx              # Chat interface
    ├── DocumentsPage.tsx         # Document management
    ├── IngestionPage.tsx         # Job monitoring
    └── KnowledgeGraphPage.tsx    # Entity explorer
```

## API Configuration

The frontend proxies API requests to the backend:

- Development: `http://localhost:8000` (via Vite proxy)
- Production: Configure in your deployment environment

All API calls are prefixed with `/api` which is rewritten to the backend URL.

## Features Overview

### Chat Page

- Multiple retrieval modes: Auto, Graph, Text, Hybrid
- Real-time streaming responses
- Evidence and source citation
- Confidence scoring

### Documents Page

- Drag-and-drop file upload
- PDF validation
- Automatic ingestion triggering
- Document listing and deletion

### Ingestion Page

- Real-time job status monitoring
- Pipeline step visualization
- Progress tracking with stats
- Auto-refresh capability

### Knowledge Graph Page

- Entity search
- Graph statistics dashboard
- Entity browsing with metadata
- Type filtering

## Environment Variables

Create a `.env` file for custom configuration:

```env
VITE_API_URL=http://localhost:8000
```

## Customization

### Colors

Edit `tailwind.config.js` to customize the color scheme:

```js
theme: {
  extend: {
    colors: {
      primary: {
        // Your color palette
      },
    },
  },
}
```

### Layout

The sidebar navigation is in `src/components/Layout.tsx`. Add or remove navigation items as needed.

## Development Tips

- Components use Tailwind's utility classes
- API types are defined in `src/lib/api.ts`
- All pages are responsive (mobile-first)
- Icons from `lucide-react` package

## License

MIT
