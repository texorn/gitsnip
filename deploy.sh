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

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Visit: https://docs.docker.com/get-docker/"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        echo "Visit: https://docs.docker.com/compose/install/"
        exit 1
    fi
    
    print_success "Docker and Docker Compose are installed"
}

# Create environment file
create_env_file() {
    if [ ! -f .env ]; then
        print_status "Creating environment file..."
        cat > .env << EOF
# GitSnip Environment Configuration

# API Keys (replace with your actual keys)
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_token_here

# Application Settings
NODE_ENV=production
FLASK_ENV=production

# Ports (change if needed)
FRONTEND_PORT=80
BACKEND_PORT=5000
PROXY_PORT=8080

# Domain (for production deployment)
DOMAIN=localhost
EOF
        print_success "Environment file created (.env)"
        print_warning "Please edit .env file and add your API keys"
    else
        print_status "Environment file already exists"
    fi
}

# Deploy frontend only
deploy_frontend() {
    print_status "Deploying GitSnip Frontend..."
    
    # Build and start frontend
    docker-compose up -d frontend
    
    print_success "Frontend deployed successfully!"
    print_status "Frontend is available at: http://localhost"
    print_status "Health check: http://localhost/health"
}

# Deploy full stack
deploy_fullstack() {
    print_status "Deploying GitSnip Full Stack..."
    
    # Build and start all services
    docker-compose --profile backend up -d
    
    print_success "Full stack deployed successfully!"
    print_status "Frontend: http://localhost"
    print_status "Backend API: http://localhost:5000"
    print_status "Health checks:"
    print_status "  - Frontend: http://localhost/health"
    print_status "  - Backend: http://localhost:5000/health"
}

# Deploy with proxy
deploy_with_proxy() {
    print_status "Deploying GitSnip with Reverse Proxy..."
    
    # Create nginx proxy config
    cat > nginx-proxy.conf << EOF
upstream frontend {
    server frontend:80;
}

upstream backend {
    server backend:5000;
}

server {
    listen 80;
    server_name localhost;

    # Frontend
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    # Backend API
    location /api/ {
        proxy_pass http://backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    
    # Build and start all services with proxy
    docker-compose --profile backend --profile proxy up -d
    
    print_success "GitSnip deployed with reverse proxy!"
    print_status "Access via: http://localhost:8080"
}

# Stop all services
stop_services() {
    print_status "Stopping GitSnip services..."
    docker-compose down
    print_success "All services stopped"
}

# Show logs
show_logs() {
    print_status "Showing GitSnip logs..."
    docker-compose logs -f
}

# Show status
show_status() {
    print_status "GitSnip Service Status:"
    docker-compose ps
    
    echo ""
    print_status "Health Checks:"
    
    # Check frontend
    if curl -s http://localhost/health > /dev/null 2>&1; then
        print_success "Frontend: Healthy"
    else
        print_error "Frontend: Unhealthy or not running"
    fi
    
    # Check backend
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        print_success "Backend: Healthy"
    else
        print_warning "Backend: Not running or unhealthy"
    fi
}

# Main menu
show_menu() {
    echo ""
    echo "Select deployment option:"
    echo "1) Deploy Frontend Only (Recommended for quick start)"
    echo "2) Deploy Full Stack (Frontend + Backend)"
    echo "3) Deploy with Reverse Proxy (Production setup)"
    echo "4) Stop All Services"
    echo "5) Show Logs"
    echo "6) Show Status"
    echo "7) Exit"
    echo ""
}

# Main script
main() {
    check_docker
    create_env_file
    
    while true; do
        show_menu
        read -p "Enter your choice (1-7): " choice
        
        case $choice in
            1)
                deploy_frontend
                ;;
            2)
                deploy_fullstack
                ;;
            3)
                deploy_with_proxy
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

