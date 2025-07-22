# Docker Setup Guide for GitSnip

This guide helps you set up Docker on different systems when the automatic setup doesn't work.

## Quick Solutions

### Option 1: Use Development Mode (Recommended)
If you're having Docker permission issues, use Development Mode instead:

```bash
./deploy.sh
# Select option 3: "Development Mode (No Docker)"
```

This bypasses Docker entirely and runs GitSnip directly with Python and Node.js.

### Option 2: Manual Docker Group Setup

#### For Ubuntu/Debian systems:
```bash
# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and log back in, then test
docker run hello-world
```

#### For systems without usermod:
```bash
# Check if docker group exists
getent group docker

# If it doesn't exist, create it
sudo groupadd docker

# Add user manually (replace 'username' with your username)
sudo gpasswd -a username docker

# Restart Docker service
sudo systemctl restart docker

# Log out and log back in
```

#### For macOS:
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Docker Desktop handles permissions automatically
```

#### For Windows:
```bash
# Install Docker Desktop from https://docker.com/products/docker-desktop
# Or use WSL2 with Linux Docker setup
```

## Alternative: Run with Sudo

If you can't fix Docker permissions, you can run GitSnip with sudo:

```bash
# Make sure the script uses sudo for Docker commands
sudo ./deploy.sh
```

## System-Specific Issues

### Alpine Linux:
```bash
# Install shadow package for usermod
sudo apk add shadow

# Then follow Ubuntu instructions
sudo usermod -aG docker $USER
```

### CentOS/RHEL:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

### Arch Linux:
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Start Docker service
sudo systemctl start docker
sudo systemctl enable docker
```

## Verification

Test your Docker setup:

```bash
# This should work without sudo
docker run hello-world

# Check Docker Compose
docker-compose --version
```

## Still Having Issues?

1. **Use Development Mode**: Run `./deploy.sh` and select option 3
2. **Check Docker installation**: `docker --version`
3. **Check Docker service**: `sudo systemctl status docker`
4. **Restart Docker**: `sudo systemctl restart docker`
5. **Reboot system**: Sometimes a full reboot is needed after adding user to docker group

## Development Mode Benefits

- ✅ No Docker permissions needed
- ✅ Faster startup (no container building)
- ✅ Direct access to logs and debugging
- ✅ Works on any system with Python 3.11+ and Node.js 20+
- ✅ Automatic dependency installation
- ✅ Same functionality as Docker mode

Choose Development Mode if you want to get started quickly without Docker complexity!

