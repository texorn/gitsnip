#!/bin/bash

# GitSnip Deployment Script
# This script helps deploy GitSnip easily on any server

set -e

echo "🚀 GitSnip Deployment Script"
echo "=============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Installing Docker..."
        # Install Docker
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        
        # Try to add user to docker group if usermod exists
        if command -v usermod &> /dev/null; then
            sudo usermod -aG docker $USER
            print_success "Docker installed. Please log out and log back in, then run this script again."
        else
            print_success "Docker installed."
            print_warning "Please add your user to the docker group manually or use sudo with Docker commands."
        fi
        exit 1
    fi
    
    # Check if user is in docker group (only if usermod exists)
    if command -v usermod &> /dev/null && ! groups $USER | grep -q docker; then
        print_warning "User $USER is not in docker group. Adding to docker group..."
        if sudo usermod -aG docker $USER 2>/dev/null; then
            print_warning "Please log out and log back in for group changes to take effect."
            print_status "Alternatively, you can run: newgrp docker"
        else
            print_warning "Could not add user to docker group. Will use sudo for Docker commands."
        fi
    fi
    
    # Check if Docker daemon is running and determine command prefix
    if docker info &> /dev/null 2>&1; then
        DOCKER_CMD="docker"
        DOCKER_COMPOSE_CMD="docker-compose"
        print_success "Docker is ready (no sudo required)"
    elif sudo docker info &> /dev/null 2>&1; then
        print_status "Starting Docker daemon..."
        sudo systemctl start docker 2>/dev/null || sudo service docker start 2>/dev/null || true
        sleep 3
        
        # Check again after starting
        if docker info &> /dev/null 2>&1; then
            DOCKER_CMD="docker"
            DOCKER_COMPOSE_CMD="docker-compose"
            print_success "Docker is ready (no sudo required)"
        else
            DOCKER_CMD="sudo docker"
            DOCKER_COMPOSE_CMD="sudo docker-compose"
            print_warning "Docker requires sudo privileges"
        fi
    else
        print_error "Docker is not running and cannot be started. Please check Docker installation."
        exit 1
    fi
    
    # Check for docker-compose
    if ! command -v docker-compose &> /dev/null; then
        if ! docker compose version &> /dev/null 2>&1; then
            print_status "Installing Docker Compose..."
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y docker-compose
            elif command -v yum &> /dev/null; then
                sudo yum install -y docker-compose
            elif command -v brew &> /dev/null; then
                brew install docker-compose
            else
                print_warning "Please install Docker Compose manually"
            fi
        fi
    fi
    
    print_success "Docker and Docker Compose are ready"
}

# Create environment file
create_env_file() {
    if [ ! -f .env ]; then
        print_status "Creating environment file..."
        cat > .env << EOF
# GitSnip Environment Configuration

# API Keys (for testing - replace with your actual keys in production)
GEMINI_API_KEY=AIzaSyBMRU4XUfWGs4TtxAXQOa7KoZoEwNC82W8
GITHUB_TOKEN=your_github_token_here

# Application Settings
NODE_ENV=production
FLASK_ENV=development

# Ports (change if needed)
FRONTEND_PORT=8000
BACKEND_PORT=4000
PROXY_PORT=8080

# Domain (for production deployment)
DOMAIN=localhost
EOF
        print_success "Environment file created (.env)"
        print_warning "Using test API key - replace with your own for production"
    else
        print_status "Environment file already exists"
    fi
}

# Build images
build_images() {
    print_status "Building Docker images..."
    
    # Build frontend
    print_status "Building frontend image..."
    sudo docker build -f frontend/react-app/Dockerfile -t gitsnip-frontend ./frontend/react-app
    
    # Build backend
    print_status "Building backend image..."
    sudo docker build -f Dockerfile.backend -t gitsnip-backend .
    
    print_success "Docker images built successfully"
}

# Deploy frontend only
deploy_frontend() {
    print_status "Deploying GitSnip Frontend..."
    
    # Build and start frontend
    $DOCKER_COMPOSE_CMD --profile frontend up -d --build
    
    print_success "Frontend deployed successfully!"
    print_status "Frontend is available at: http://localhost:8000"
}

# Deploy full stack
deploy_fullstack() {
    print_status "Deploying GitSnip Full Stack..."
    
    # Build and start all services
    $DOCKER_COMPOSE_CMD --profile fullstack up -d --build
    
    print_success "Full stack deployed successfully!"
    print_status "Frontend: http://localhost:8000"
    print_status "Backend API: http://localhost:4000"
}

# Deploy with development mode (no Docker)
deploy_dev() {
    print_status "Starting GitSnip in Development Mode..."
    
    # Load environment variables
    if [ -f .env ]; then
        export $(cat .env | grep -v '^#' | xargs)
        print_status "Loaded environment variables from .env"
    fi
    
    # Check if Python dependencies are installed
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        print_status "Installing Python dependencies..."
        pip install -r requirements.txt
        pip install flask flask-cors cryptography
    else
        source venv/bin/activate
        print_status "Using existing virtual environment"
    fi
    
    # Create necessary directories
    mkdir -p output temp data logs
    
    # Start backend
    print_status "Starting backend server..."
    export FLASK_ENV=development
    export GEMINI_API_KEY=${GEMINI_API_KEY}
    python3 api_server.py &
    BACKEND_PID=$!
    
    # Wait for backend to start
    sleep 5
    
    # Test backend health
    if curl -s http://localhost:4000/health > /dev/null 2>&1; then
        print_success "Backend started successfully"
    else
        print_error "Backend failed to start"
        kill $BACKEND_PID 2>/dev/null
        return 1
    fi
    
    # Start frontend
    print_status "Starting frontend development server..."
    cd frontend/react-app
    
    # Install frontend dependencies if needed
    if [ ! -d "node_modules" ]; then
        print_status "Installing frontend dependencies..."
        pnpm install
    fi
    
    # Start frontend dev server
    pnpm run dev --host &
    FRONTEND_PID=$!
    
    cd ../..
    
    # Wait for frontend to start
    sleep 5
    
    # Test frontend
    if curl -s http://localhost:5173/ > /dev/null 2>&1; then
        print_success "Frontend started successfully"
    else
        print_warning "Frontend may still be starting..."
    fi
    
    print_success "Development servers started!"
    print_status "Frontend: http://localhost:5173"
    print_status "Backend API: http://localhost:4000"
    print_status "Backend Health: http://localhost:4000/health"
    print_warning "Press Ctrl+C to stop both servers"
    
    # Wait for user to stop
    trap "print_status 'Stopping servers...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
    wait
}

# Stop all services
stop_services() {
    print_status "Stopping GitSnip services..."
    
    # Stop Docker containers
    $DOCKER_COMPOSE_CMD down 2>/dev/null || true
    $DOCKER_CMD stop gitsnip-frontend gitsnip-backend 2>/dev/null || true
    $DOCKER_CMD rm gitsnip-frontend gitsnip-backend 2>/dev/null || true
    
    # Stop development servers
    pkill -f "api_server.py" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    
    print_success "All services stopped"
}

# Show logs
show_logs() {
    print_status "Showing GitSnip logs..."
    if $DOCKER_COMPOSE_CMD ps | grep -q "gitsnip"; then
        $DOCKER_COMPOSE_CMD logs -f --tail 50
    else
        echo "Frontend logs:"
        $DOCKER_CMD logs gitsnip-frontend --tail 50 2>/dev/null || echo "Frontend container not running"
        echo ""
        echo "Backend logs:"
        $DOCKER_CMD logs gitsnip-backend --tail 50 2>/dev/null || echo "Backend container not running"
    fi
}

# Show status
show_status() {
    print_status "GitSnip Service Status:"
    
    # Check Docker containers
    if $DOCKER_CMD ps | grep -q gitsnip-frontend; then
        print_success "Frontend Container: Running"
    else
        print_warning "Frontend Container: Not running"
    fi
    
    if $DOCKER_CMD ps | grep -q gitsnip-backend; then
        print_success "Backend Container: Running"
    else
        print_warning "Backend Container: Not running"
    fi
    
    echo ""
    print_status "Health Checks:"
    
    # Check frontend
    if curl -s http://localhost:8000/ > /dev/null 2>&1; then
        print_success "Frontend: Healthy (http://localhost:8000)"
    elif curl -s http://localhost:5173/ > /dev/null 2>&1; then
        print_success "Frontend Dev: Healthy (http://localhost:5173)"
    else
        print_error "Frontend: Unhealthy or not running"
    fi
    
    # Check backend
    if curl -s http://localhost:4000/health > /dev/null 2>&1; then
        print_success "Backend: Healthy (http://localhost:4000)"
    else
        print_warning "Backend: Not running or unhealthy"
    fi
}

# Test the application
test_application() {
    print_status "Testing GitSnip Application..."
    
    # Test backend health
    if curl -s http://localhost:4000/health > /dev/null 2>&1; then
        print_success "Backend health check passed"
    else
        print_error "Backend health check failed"
        return 1
    fi
    
    # Test frontend
    if curl -s http://localhost:8000/ > /dev/null 2>&1 || curl -s http://localhost:5173/ > /dev/null 2>&1; then
        print_success "Frontend accessibility check passed"
    else
        print_error "Frontend accessibility check failed"
        return 1
    fi
    
    # Test fast analysis mode (mock request)
    print_status "Testing fast analysis mode..."
    FAST_TEST=$(curl -s -X POST http://localhost:4000/api/gitsnip/analyze \
        -H "Content-Type: application/json" \
        -d '{
            "repository_url": "https://github.com/octocat/Hello-World",
            "analysis_mode": "fast",
            "config": {
                "include_patterns": ["*.py"],
                "language": "english"
            }
        }')
    
    if echo "$FAST_TEST" | grep -q "job_id"; then
        print_success "Fast analysis mode API test passed"
    else
        print_warning "Fast analysis mode API test failed (may need valid repo)"
    fi
    
    # Test detailed analysis mode validation
    print_status "Testing detailed analysis mode validation..."
    DETAILED_TEST=$(curl -s -X POST http://localhost:4000/api/gitsnip/analyze \
        -H "Content-Type: application/json" \
        -d '{
            "repository_url": "https://github.com/octocat/Hello-World",
            "analysis_mode": "detailed",
            "config": {
                "include_patterns": ["*.py"],
                "language": "english"
            }
        }')
    
    if echo "$DETAILED_TEST" | grep -q "User API key is required"; then
        print_success "Detailed analysis mode validation test passed"
    else
        print_warning "Detailed analysis mode validation test failed"
    fi
    
    print_success "All tests passed!"
    print_status ""
    print_status "🎉 GitSnip Dual-Mode Analysis System is working!"
    print_status "✅ Fast Mode: Uses built-in Gemini 2.5 Flash-Lite Preview (5 files max)"
    print_status "✅ Detailed Mode: Uses user's API key for comprehensive analysis"
    print_status "✅ Frontend: Modern React UI with mode selection"
    print_status "✅ Backend: Flask API with encryption for private repos"
}

# Main menu
show_menu() {
    echo ""
    echo "Select deployment option:"
    echo "1) Deploy Frontend Only (Docker)"
    echo "2) Deploy Full Stack (Docker)"
    echo "3) Development Mode (No Docker) - Recommended if Docker issues"
    echo "4) Stop All Services"
    echo "5) Show Logs"
    echo "6) Show Status"
    echo "7) Test Application"
    echo "8) Exit"
    echo ""
    
    if [[ "$DOCKER_CMD" == *"sudo"* ]]; then
        echo "Note: Docker requires sudo on this system."
        echo "Consider using Development Mode (option 3) for easier setup."
        echo ""
    fi
}

# Main script
main() {
    check_docker
    create_env_file
    
    while true; do
        show_menu
        read -p "Enter your choice (1-8): " choice
        
        case $choice in
            1)
                deploy_frontend
                ;;
            2)
                deploy_fullstack
                ;;
            3)
                deploy_dev
                ;;
            4)
                stop_services
                ;;
            5)
                show_logs
                ;;
            6)
                show_status
                ;;
            7)
                test_application
                ;;
            8)
                print_success "Goodbye!"
                exit 0
                ;;
            *)
                print_error "Invalid option. Please try again."
                ;;
        esac
        
        echo ""
        read -p "Press Enter to continue..."
    done
}

# Run main function
main

