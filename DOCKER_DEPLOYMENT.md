# 🐳 GitSnip Docker Deployment Guide

This guide provides multiple ways to deploy GitSnip using Docker, from simple local development to production-ready setups on VPS servers like Hostinger.

## 🚀 Quick Start (Recommended)

### Option 1: One-Command Deployment

```bash
# Clone the repository
git clone https://github.com/texorn/gitsnip.git
cd gitsnip

# Run the interactive deployment script
./deploy.sh
```

The script will guide you through the deployment process with a simple menu.

### Option 2: Manual Docker Commands

```bash
# Frontend only (fastest setup)
docker-compose up -d frontend

# Full stack (frontend + backend)
docker-compose --profile backend up -d

# With reverse proxy (production)
docker-compose --profile backend --profile proxy up -d
```

## 📋 Prerequisites

- **Docker** (version 20.0+)
- **Docker Compose** (version 2.0+)
- **Git** (for cloning the repository)

### Installing Docker

#### Ubuntu/Debian (Hostinger VPS)
```bash
# Update package index
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

#### Other Systems
- **Windows/Mac**: Install [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **CentOS/RHEL**: Follow [official Docker docs](https://docs.docker.com/engine/install/)

## 🏗️ Deployment Options

### 1. Frontend Only (Quick Demo)

Perfect for testing the UI without backend functionality.

```bash
# Start frontend
docker-compose up -d frontend

# Access at http://localhost
# Health check: http://localhost/health
```

**Features:**
- ✅ Complete React UI
- ✅ All frontend functionality
- ✅ Responsive design
- ❌ No backend integration (simulated data)

### 2. Full Stack (Complete Application)

Includes both frontend and backend with API integration.

```bash
# Start full stack
docker-compose --profile backend up -d

# Frontend: http://localhost
# Backend API: http://localhost:5000
```

**Features:**
- ✅ Complete React UI
- ✅ Python backend API
- ✅ Real GitSnip analysis
- ✅ Full workflow integration

### 3. Production Setup (Reverse Proxy)

Production-ready setup with reverse proxy for better performance.

```bash
# Start with reverse proxy
docker-compose --profile backend --profile proxy up -d

# Access via: http://localhost:8080
```

**Features:**
- ✅ Reverse proxy (Nginx)
- ✅ Load balancing
- ✅ Better security
- ✅ Production optimizations

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_token_here

# Application Settings
NODE_ENV=production
FLASK_ENV=production

# Ports
FRONTEND_PORT=80
BACKEND_PORT=5000
PROXY_PORT=8080

# Domain (for production)
DOMAIN=your-domain.com
```

### Custom Ports

To use different ports, modify `docker-compose.yml`:

```yaml
services:
  frontend:
    ports:
      - "8080:80"  # Change 8080 to your desired port
```

## 🌐 VPS Deployment (Hostinger/DigitalOcean/AWS)

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

# Deploy
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

If you have a domain, point it to your VPS IP and update nginx configuration:

```bash
# Edit nginx config
nano nginx-proxy.conf

# Change server_name from localhost to your domain
server_name your-domain.com;
```

## 🔧 Management Commands

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f frontend
docker-compose logs -f backend
```

### Stop Services
```bash
# Stop all
docker-compose down

# Stop specific profile
docker-compose --profile backend down
```

### Update Application
```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose down
docker-compose up -d --build
```

### Monitor Resources
```bash
# View running containers
docker ps

# View resource usage
docker stats

# View service status
docker-compose ps
```

## 🔍 Troubleshooting

### Common Issues

#### Port Already in Use
```bash
# Check what's using the port
sudo lsof -i :80

# Kill the process or change port in docker-compose.yml
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

#### Container Won't Start
```bash
# Check logs
docker-compose logs [service-name]

# Check container status
docker ps -a
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

## 📊 Performance Optimization

### For Production

1. **Enable SSL/HTTPS**
   ```bash
   # Install Certbot
   sudo apt install certbot python3-certbot-nginx
   
   # Get SSL certificate
   sudo certbot --nginx -d your-domain.com
   ```

2. **Optimize Docker Images**
   ```bash
   # Use multi-stage builds (already implemented)
   # Enable BuildKit for faster builds
   export DOCKER_BUILDKIT=1
   ```

3. **Resource Limits**
   ```yaml
   # Add to docker-compose.yml
   services:
     frontend:
       deploy:
         resources:
           limits:
             memory: 512M
             cpus: '0.5'
   ```

### For Development

```bash
# Development mode with hot reload
cd frontend/react-app
pnpm install
pnpm run dev --host

# Backend development
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

## 🔐 Security Considerations

1. **Change Default Ports** in production
2. **Use Strong API Keys** in `.env` file
3. **Enable Firewall** on VPS
4. **Regular Updates** of Docker images
5. **SSL/HTTPS** for production domains
6. **Backup Data** regularly

## 📈 Scaling

### Horizontal Scaling
```yaml
# Scale frontend instances
docker-compose up -d --scale frontend=3

# Use load balancer
# Configure nginx upstream with multiple backends
```

### Vertical Scaling
```yaml
# Increase resource limits
deploy:
  resources:
    limits:
      memory: 2G
      cpus: '2.0'
```

## 🆘 Support

If you encounter issues:

1. Check the [troubleshooting section](#troubleshooting)
2. View logs: `docker-compose logs -f`
3. Check service status: `./deploy.sh` → option 6
4. Open an issue on GitHub with logs and error details

## 📝 Quick Reference

| Command | Description |
|---------|-------------|
| `./deploy.sh` | Interactive deployment |
| `docker-compose up -d frontend` | Frontend only |
| `docker-compose --profile backend up -d` | Full stack |
| `docker-compose down` | Stop all services |
| `docker-compose logs -f` | View logs |
| `docker-compose ps` | Service status |

---

**🎉 That's it! GitSnip should now be running and accessible via your browser.**

For questions or support, please open an issue on the GitHub repository.

