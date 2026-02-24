# Frontend

React 19 + TypeScript + Tailwind CSS frontend for FastAPI Enterprise Boilerplate.

## Quick Start

### Local Development

```bash
# Install dependencies
npm install

# Start development server
npm run dev
# Access at http://localhost:3000
```

### Docker Development

```bash
# From project root
docker compose up -d

# Frontend available at http://localhost:3000
# Hot-reload enabled with volume mounting
```

### Production Build

```bash
# Build for production
npm run build

# Or with Docker
docker compose -f docker-compose.prod.yml up --build
```

## Docker Configuration

- **Development** (`Dockerfile.dev`): Vite dev server with hot-reload on port 3000
- **Production** (`Dockerfile`): Nginx serving optimized static files on port 80

## Project Structure

```text
src/
├── components/          # Reusable UI components
│   └── layouts/         # Page layouts
├── hooks/               # Custom React hooks
├── pages/               # Page components (route-based)
├── services/            # API client and services
├── stores/              # Zustand state stores
└── utils/               # Utility functions
```

## Available Scripts

| Command              | Description                           |
| -------------------- | ------------------------------------- |
| `npm run dev`        | Start development server on port 3000 |
| `npm run build`      | Build for production                  |
| `npm run preview`    | Preview production build              |
| `npm run lint`       | Run ESLint                            |
| `npm run test`       | Run tests                             |
| `npm run type-check` | TypeScript type checking              |

## Features

- **React 19** - Latest React with TypeScript
- **TypeScript 5.7** - Full type safety
- **Tailwind CSS** - Utility-first styling
- **React Query** - Server state management
- **Zustand** - Client state management
- **React Router v6** - Client-side routing
- **React Hook Form** - Form handling
- **i18next** - Multi-language support (EN/ES/PT)
- **Lucide Icons** - Beautiful icons

## Environment Variables

Create a `.env.local` file:

```bash
VITE_API_URL=http://localhost:8000/api/v1
```

## Development

The development server proxies `/api` requests to `http://localhost:8000`, so you can run the backend locally and the frontend will communicate with it seamlessly.
