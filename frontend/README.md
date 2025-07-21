# GitSnip React Frontend

A modern, responsive React frontend for the GitSnip codebase analysis tool.

## Features

- **5-Step Workflow**: Repository → Configuration → Authentication → Processing → Results
- **Beautiful UI**: Modern design with Tailwind CSS and shadcn/ui components
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **Form Validation**: Real-time validation with helpful error messages
- **Progress Tracking**: Animated progress with realistic status updates
- **Professional Styling**: Clean, modern interface matching GitSnip branding

## Tech Stack

- React 18 with modern hooks
- Tailwind CSS for styling
- shadcn/ui component library
- Vite for development and building
- Lucide React for icons

## Installation

```bash
cd frontend/react-app
pnpm install
pnpm run dev --host
```

## Development

```bash
# Install dependencies
pnpm install

# Start development server
pnpm run dev --host

# Build for production
pnpm run build

# Preview production build
pnpm run preview
```

## Integration

The frontend is designed to integrate with the GitSnip backend API with these endpoints:

- `POST /api/gitsnip/analyze` - Start analysis
- `GET /api/gitsnip/status/{job_id}` - Check progress
- `GET /api/gitsnip/results/{job_id}` - Get results

## User Experience

The application provides a complete user experience:

1. **Repository Input** - GitHub URL validation and private repo detection
2. **Configuration** - File pattern filtering, size limits, language selection
3. **Authentication** - GitHub token input for private repositories
4. **Processing** - Animated progress with realistic status updates
5. **Results** - Comprehensive analysis display with download option

## Project Structure

```
react-app/
├── public/
├── src/
│   ├── assets/
│   ├── components/
│   │   └── ui/          # shadcn/ui components
│   ├── hooks/
│   ├── lib/
│   │   └── utils.js     # Utility functions
│   ├── App.css          # Custom styles
│   ├── App.jsx          # Main application
│   ├── index.css        # Global styles
│   └── main.jsx         # Entry point
├── components.json      # shadcn/ui config
├── package.json
├── vite.config.js
└── index.html
```

## Screenshots

The frontend provides a complete user experience from repository input to results display, with a professional interface that makes GitSnip accessible to a broader audience.

## Benefits

- **Improved UX**: Professional, intuitive interface for GitSnip users
- **Modern Stack**: Built with current best practices and technologies
- **Responsive**: Works seamlessly across all device sizes
- **Extensible**: Clean architecture ready for additional features
- **Production Ready**: Fully tested and deployment-ready

This frontend transforms GitSnip from a command-line tool into a user-friendly web application, making codebase analysis accessible to everyone.

