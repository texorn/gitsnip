# GitSnip

**Turning complex codebases into accessible stories**

[![Watch the GitSnip Demo Video](https://img.youtube.com/vi/p7L3rP_ZJHg/0.jpg)](https://youtu.be/p7L3rP_ZJHg)

![License](https://img.shields.io/badge/license-MIT-blue.svg) 
Automatically generate comprehensive, step-by-step tutorials from any codebase using AI.

## 🤔 About

Understanding large, complex real-world projects is often a developer's nightmare. With minimal documentation and intricate codebases, onboarding to new projects can take weeks of frustrating effort. After repeatedly facing this challenge throughout my career, I realized this widespread problem needed a solution.

That's why I created **GitSnip** - a tool that transforms impenetrable codebases into comprehensible narratives. GitSnip intelligently crawls through entire repositories and generates beautifully structured, story-based explanations of how the code works, complete with detailed explanations, relevant code blocks, and intuitive flow diagrams. What once took days or weeks to grasp can now be understood in hours, making the process of learning a new codebase as enjoyable as reading a well-crafted "lore" rather than a technical chore.

While initially inspired by a basic codebase knowledge generator example from PocketFlow (a 100-line minimalist LLM framework designed for building AI agent workflows), GitSnip represents a complete reimagining of the concept. I've developed advanced capabilities to handle genuinely complex, large-scale projects through sophisticated embedding-based clustering, intelligent content chunking, and cross-reference handling. These enhancements transform the concept from an interesting demo into a powerful tool capable of tackling real-world enterprise codebases that previously required extensive time and expertise to understand.

## 🚀 Features

### Core Analysis Features
-   📚 **Automated Tutorial Creation**: Generates multi-chapter Markdown tutorials from source code
-   🧠 **AI-Powered Analysis**: Leverages LLMs (Gemini) to identify core abstractions and relationships within the code
-   🔗 **Code Connectivity**: Understands how different parts of the codebase interact
-   📈 **Visual Structure**: Creates Mermaid diagrams to visualize project architecture and component relationships
-   ✨ **Diagram Validation & Fixing**: Automatically validates and attempts to fix generated Mermaid diagrams using `mmdc`
-   📂 **Flexible Input**: Works with both local directories and public/private GitHub repositories
-   🔍 **Large Codebase Handling**: Uses embedding and clustering techniques for codebases exceeding LLM context windows
-   🌐 **Language Support**: Generate tutorials in different languages (via `--language` flag, applies to generated text)
-   ⚙️ **Configurable**: Filter files using include/exclude patterns and set maximum file size limits

### Web Application Features
-   🎨 **Modern React Frontend**: Beautiful, responsive web interface with Tailwind CSS
-   🔄 **5-Step Workflow**: Repository → Configuration → Authentication → Processing → Results
-   📊 **Real-time Progress**: Live progress tracking with detailed status updates
-   🔐 **Security**: Encryption for private repository analysis results
-   📱 **Responsive Design**: Works perfectly on desktop and mobile devices
-   ⚡ **One-Command Deployment**: Deploy anywhere with Docker in seconds

## ⚙️ Tech Stack

### Backend
-   🐍 **Python 3**: Core analysis engine
-   🌊 **PocketFlow**: Workflow orchestration
-   🤖 **Google Gemini API**: AI-powered code analysis
-   🐙 **PyGithub**: GitHub repository integration
-   📊 **Mermaid.js**: Diagram generation and validation
-   🔧 **Flask**: REST API server
-   🔐 **Cryptography**: Secure encryption for private repos

### Frontend
-   ⚛️ **React 18**: Modern UI framework
-   🎨 **Tailwind CSS**: Utility-first styling
-   🧩 **shadcn/ui**: Professional component library
-   ⚡ **Vite**: Fast development and building
-   🎯 **Lucide React**: Beautiful icons

### Deployment
-   🐳 **Docker**: Containerized deployment
-   🌐 **Nginx**: Production web server
-   📦 **Docker Compose**: Multi-service orchestration

## 🚀 Quick Start (Recommended)

### Option 1: One-Command Deployment 🎯

The fastest way to get GitSnip running:

```bash
# Clone the repository
git clone https://github.com/texorn/gitsnip.git
cd gitsnip

# Run the interactive deployment script
./deploy.sh
```

The script will guide you through deployment options:
1. **Frontend Only** - Quick demo with simulated backend
2. **Full Stack** - Complete application with real analysis
3. **Production** - Production-ready setup with reverse proxy

### Option 2: Docker Commands

```bash
# Frontend only (fastest setup)
docker-compose up -d frontend
# Access at: http://localhost

# Full stack (frontend + backend)
docker-compose --profile backend up -d
# Frontend: http://localhost
# Backend API: http://localhost:5000

# Production setup (with reverse proxy)
docker-compose --profile backend --profile proxy up -d
# Access at: http://localhost:8080
```

### Option 3: Manual Docker Build

```bash
# Build and run frontend
cd frontend/react-app
docker build -t gitsnip-frontend .
docker run -p 80:80 gitsnip-frontend

# Build and run backend
cd ../..
docker build -f Dockerfile.backend -t gitsnip-backend .
docker run -p 5000:5000 gitsnip-backend
```

## 🛠️ Development Setup

### Prerequisites

- **Docker & Docker Compose** (recommended)
- **Node.js 20+** and **pnpm** (for frontend development)
- **Python 3.11+** (for backend development)
- **Git** (for cloning)

### Frontend Development

```bash
# Navigate to frontend
cd frontend/react-app

# Install dependencies
pnpm install

# Start development server
pnpm run dev --host
# Access at: http://localhost:5173
```

### Backend Development

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install flask flask-cors cryptography

# Set environment variables
export GEMINI_API_KEY="your_gemini_api_key_here"
export GITHUB_TOKEN="your_github_token_here"  # Optional

# Run the API server
python api_server.py
# API available at: http://localhost:5000
```

### Command Line Usage

For direct command-line usage without the web interface:

```bash
# Activate virtual environment
source venv/bin/activate

# Install Mermaid CLI (requires Node.js)
npm install -g @mermaid-js/mermaid-cli

# Analyze a local directory
python main.py --dir /path/to/your/codebase -i "*.py" -o ./output-directory

# Analyze a GitHub repository
python main.py --repo https://github.com/owner/repo -i "*.ts" -o ./output-directory

# For private repositories, clone first then use --dir
git clone https://github.com/owner/private-repo.git
python main.py --dir ./private-repo -i "*.js" -o ./output-directory
```

## 🌐 VPS Deployment

Deploy GitSnip on any VPS (Hostinger, DigitalOcean, AWS, etc.):

### Step 1: Server Setup

```bash
# Connect to your VPS
ssh root@your-server-ip

# Update system
apt update && apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Install Docker Compose
apt install docker-compose-plugin -y
```

### Step 2: Deploy GitSnip

```bash
# Clone repository
git clone https://github.com/texorn/gitsnip.git
cd gitsnip

# Create environment file
cp .env.example .env
nano .env  # Edit with your API keys

# Deploy with interactive script
./deploy.sh
```

### Step 3: Configure Firewall

```bash
# Allow HTTP/HTTPS traffic
ufw allow 80
ufw allow 443
ufw allow 22  # SSH
ufw enable
```

### Step 4: Domain Setup (Optional)

Point your domain to the VPS IP and update nginx configuration:

```bash
# Edit nginx config
nano nginx-proxy.conf

# Change server_name from localhost to your domain
server_name your-domain.com;

# Restart services
docker-compose restart
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys (Required)
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_token_here

# Application Settings
NODE_ENV=production
FLASK_ENV=production

# Ports (Optional - change if needed)
FRONTEND_PORT=80
BACKEND_PORT=5000
PROXY_PORT=8080

# Domain (For production)
DOMAIN=your-domain.com
```

### API Keys Setup

1. **Gemini API Key**: Get from [Google AI Studio](https://aistudio.google.com/app/apikey)
2. **GitHub Token**: Generate from [GitHub Settings](https://github.com/settings/tokens)
   - Required permissions: `repo` (for private repos), `public_repo` (for public repos)

## 🔐 Security Features

### Private Repository Protection

GitSnip includes advanced security features for private repository analysis:

- **🔒 Encryption**: Results encrypted using your GitHub token as the key
- **🛡️ No Plain Text Storage**: Private repo analysis never stored unencrypted
- **🔑 Token Verification**: Only you can decrypt your results
- **🗑️ Auto Cleanup**: Unencrypted files automatically removed
- **📥 Secure Downloads**: Encrypted archives for private repo results

### Security Flow

1. **Private Repo Detected** → Automatic encryption enabled
2. **Analysis Complete** → Results encrypted with your GitHub token
3. **View Results** → Click "View Results" to decrypt with your token
4. **Download** → Secure download with token authentication

## 📊 Usage Examples

### Web Interface

1. **Open GitSnip** in your browser (http://localhost after deployment)
2. **Enter Repository URL** (e.g., `https://github.com/facebook/react`)
3. **Configure Analysis** (file patterns, size limits, language)
4. **Authenticate** (GitHub token for private repos)
5. **Monitor Progress** (real-time updates)
6. **View Results** (comprehensive analysis with download option)

### Command Line

```bash
# Analyze a Python project
python main.py --repo https://github.com/django/django \
  --include "*.py" \
  --exclude "*/tests/*" \
  --max-file-size 50000 \
  --language english \
  --output ./django-analysis

# Analyze a JavaScript project
python main.py --dir ./my-react-app \
  --include "*.js,*.jsx,*.ts,*.tsx" \
  --exclude "node_modules/*,build/*" \
  --output ./react-analysis

# Analyze with custom settings
python main.py --repo https://github.com/microsoft/vscode \
  --include "*.ts,*.js" \
  --exclude "*/test/*,*/node_modules/*" \
  --max-file-size 100000 \
  --language spanish \
  --output ./vscode-analysis
```

## 🔧 Management Commands

### Docker Management

```bash
# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Update application
git pull origin main
docker-compose down
docker-compose up -d --build

# View service status
docker-compose ps

# Monitor resources
docker stats
```

### Health Checks

```bash
# Frontend health
curl http://localhost/health

# Backend health
curl http://localhost:5000/health

# Check all services
./deploy.sh  # Choose option 6 (Show Status)
```

## 🔍 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :80

# Change port in docker-compose.yml or kill the process
```

#### Permission Denied
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Logout and login again
```

#### Out of Disk Space
```bash
# Clean up Docker
docker system prune -a

# Remove unused volumes
docker volume prune
```

#### Analysis Takes Too Long
- Large codebases can take 2-3 hours or more
- Consider using file filters to reduce scope
- Check API rate limits (try Gemini 2.5 Pro Preview)
- Monitor progress in the web interface

### Getting Help

1. Check the [troubleshooting section](#troubleshooting)
2. View logs: `docker-compose logs -f`
3. Check service status: `./deploy.sh` → option 6
4. Open an issue on GitHub with logs and error details

## 📝 Output Structure

GitSnip generates comprehensive documentation:

```
output-directory/
├── Project_Name/
│   ├── README.md              # Main tutorial with table of contents
│   ├── 01_component_name.md   # Individual component chapters
│   ├── 02_another_component.md
│   ├── ...
│   └── diagrams/              # Generated Mermaid diagrams
│       ├── overview.mmd
│       └── component_*.mmd
```

### Viewing Results

- **Web Interface**: Results displayed with syntax highlighting and download option
- **Local Files**: Use VSCode with "Markdown Preview Enhanced" extension
- **Command Line**: Navigate to output directory and open `README.md`

## 🤝 Contributing

Contributions are welcome! Here's how to get started:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes** and test thoroughly
4. **Commit your changes**: `git commit -m 'Add amazing feature'`
5. **Push to the branch**: `git push origin feature/amazing-feature`
6. **Open a Pull Request**

### Development Guidelines

- Follow existing code style and conventions
- Add tests for new features
- Update documentation as needed
- Test Docker deployment before submitting

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

-   Built using the excellent [PocketFlow](https://github.com/The-Pocket/pocketflow) library
-   Powered by Google's [Gemini](https://deepmind.google.com/technologies/gemini/) models
-   Diagrams created with [Mermaid.js](https://mermaid.js.org/)
-   UI components from [shadcn/ui](https://ui.shadcn.com/)
-   Icons from [Lucide](https://lucide.dev/)

## 🚀 What's New

### Recent Updates

- ✅ **React Frontend**: Modern web interface with beautiful UI
- ✅ **Docker Deployment**: One-command deployment anywhere
- ✅ **Security Features**: Encryption for private repository analysis
- ✅ **Real Backend Integration**: No more placeholders - real GitSnip analysis
- ✅ **VPS Ready**: Deploy on Hostinger, DigitalOcean, AWS, etc.
- ✅ **Production Ready**: Health checks, monitoring, reverse proxy

### Roadmap

- 🔄 **Multi-language Support**: Support for more programming languages
- 📊 **Analytics Dashboard**: Usage statistics and insights
- 🔗 **API Integrations**: Connect with popular development tools
- 🎨 **Custom Themes**: Personalized UI themes and branding
- 📱 **Mobile App**: Native mobile application
- 🤖 **AI Improvements**: Enhanced analysis with newer models

---

**🎉 GitSnip transforms complex codebases into accessible stories. Start your journey today!**

For questions, issues, or feature requests, please visit our [GitHub repository](https://github.com/texorn/gitsnip).

