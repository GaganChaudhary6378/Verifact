# VeriFact Deployment Script Guide

Complete automated deployment solution for building and deploying the VeriFact backend to AWS EC2.

---

## 🚀 Quick Start

### Basic Deployment

```bash
cd /Users/apple/Developer/KD/ai-league/week-1/backend
./deploy.sh
```

This will:
1. ✅ Build multi-architecture Docker image (amd64 + arm64)
2. ✅ Push to Docker Hub
3. ✅ Deploy to EC2 instance
4. ✅ Restart services with zero downtime
5. ✅ Verify deployment health

---

## 📋 Prerequisites

Before running the deployment script, ensure:

- [x] Docker installed and running
- [x] Docker Hub account configured
- [x] SSH key available at `~/.ssh/verifact-key`
- [x] EC2 instance running and accessible
- [x] You're in the backend directory

---

## 🛠️ Usage

### Standard Deployment

Deploy latest code to production:

```bash
./deploy.sh
```

### Dry Run Mode

Test the build without deploying:

```bash
./deploy.sh --dry-run
```

This will:
- Build the Docker image locally
- **NOT** push to Docker Hub
- **NOT** deploy to EC2
- Show what would be executed

### Custom Configuration

Override defaults with environment variables:

```bash
# Custom Docker Hub username
DOCKER_USERNAME=myusername ./deploy.sh

# Custom image name
IMAGE_NAME=my-backend ./deploy.sh

# Custom version tag
VERSION=v1.2.3 ./deploy.sh

# Custom EC2 host
EC2_HOST=52.1.2.3 ./deploy.sh

# Custom SSH key location
SSH_KEY=/path/to/my-key.pem ./deploy.sh

# Combine multiple options
DOCKER_USERNAME=myuser VERSION=v2.0.0 EC2_HOST=52.1.2.3 ./deploy.sh
```

---

## 📊 What the Script Does

### Step 1: Pre-flight Checks ✈️

Validates:
- Docker is installed and running
- Dockerfile exists
- SSH key exists and has correct permissions (400)
- Docker Hub login status
- EC2 instance connectivity

### Step 2: Build Docker Image 🐳

- Uses Docker Buildx for multi-architecture builds
- Builds for `linux/amd64` (EC2) and `linux/arm64` (Apple Silicon)
- Tags with version and `latest`
- Pushes to Docker Hub

### Step 3: Verify Connectivity 🔌

- Tests SSH connection to EC2 instance
- Verifies instance is reachable
- Checks security group allows access

### Step 4: Check Current Status 📊

- Shows current container status
- Displays running services
- Captures pre-deployment state

### Step 5: Deploy to EC2 🚀

On the EC2 instance:
1. Pulls latest Docker image
2. Stops backend container (gracefully)
3. Removes old container
4. Starts new container
5. Waits for health check (max 60 seconds)
6. Shows deployment status

### Step 6: Verify Deployment ✅

- Tests health endpoint
- Displays API response
- Shows logs if health check fails
- Provides deployment summary

---

## 🎯 Default Configuration

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `DOCKER_USERNAME` | `kickdrishu` | Docker Hub username |
| `IMAGE_NAME` | `ai-league-codesurgeons` | Docker image name |
| `VERSION` | `latest` | Image version tag |
| `EC2_HOST` | `43.205.75.204` | EC2 instance IP address |
| `SSH_KEY` | `~/.ssh/verifact-key` | SSH private key path |
| `SSH_USER` | `ec2-user` | SSH username |

---

## 📝 Example Workflows

### 1. Deploy After Code Changes

```bash
# Make code changes
vim src/api/main.py

# Deploy
cd /Users/apple/Developer/KD/ai-league/week-1/backend
./deploy.sh
```

### 2. Deploy with Custom Version

```bash
# Deploy specific version
VERSION=v1.5.0 ./deploy.sh

# This creates:
# - kickdrishu/ai-league-codesurgeons:v1.5.0
# - kickdrishu/ai-league-codesurgeons:latest
```

### 3. Test Build Before Deploying

```bash
# Dry run to verify build
./deploy.sh --dry-run

# If successful, deploy for real
./deploy.sh
```

### 4. Deploy to Different Environment

```bash
# Deploy to staging server
EC2_HOST=staging.example.com SSH_KEY=~/.ssh/staging-key.pem ./deploy.sh

# Deploy to production
EC2_HOST=prod.example.com SSH_KEY=~/.ssh/prod-key.pem ./deploy.sh
```

---

## 🔍 Script Output

### Successful Deployment

```
═══════════════════════════════════════════════════════════════════
VeriFact Complete Deployment
═══════════════════════════════════════════════════════════════════
Docker Image: kickdrishu/ai-league-codesurgeons:latest
EC2 Instance: ec2-user@43.205.75.204
Backend Directory: /Users/apple/Developer/KD/ai-league/week-1/backend
═══════════════════════════════════════════════════════════════════

[1/6] Running pre-flight checks...
✓ Pre-flight checks passed

[2/6] Building multi-architecture Docker image...
... (build output) ...
✓ Docker image built successfully

[3/6] Verifying EC2 instance connectivity...
✓ EC2 instance is reachable

[4/6] Checking current backend status...
Current containers:
NAME                IMAGE                                    STATUS
verifact-backend    kickdrishu/ai-league-codesurgeons:latest Up 2 hours

[5/6] Deploying to EC2 instance...
... (deployment output) ...
✓ Deployment completed on EC2

[6/6] Verifying deployment...
✓ Health check passed!
{
  "status": "healthy",
  "service": "verifact",
  "version": "1.0.0"
}

═══════════════════════════════════════════════════════════════════
✓ Complete Deployment Successful!
═══════════════════════════════════════════════════════════════════

Deployment Summary:
  • Image: kickdrishu/ai-league-codesurgeons:latest
  • Pushed to Docker Hub: Yes
  • Deployed to EC2: Yes
  • Backend URL: http://43.205.75.204:8000
  • API Docs: http://43.205.75.204:8000/docs
  • Health Check: http://43.205.75.204:8000/health
```

---

## 🐛 Troubleshooting

### Issue: "Docker is not installed"

**Solution:**
```bash
# Install Docker Desktop for Mac
brew install --cask docker

# Start Docker Desktop
open -a Docker
```

### Issue: "SSH key not found"

**Solution:**
```bash
# Verify key exists
ls -la ~/.ssh/verifact-key

# If missing, regenerate (see DEPLOYMENT_INFO.md)
# Or specify custom location:
SSH_KEY=/path/to/your/key.pem ./deploy.sh
```

### Issue: "Cannot connect to EC2 instance"

**Causes & Solutions:**

1. **Instance not running:**
   ```bash
   # Check instance status
   aws ec2 describe-instances --instance-ids i-0a32d41f315ed7a4a --region ap-south-1
   ```

2. **Security group blocks SSH:**
   ```bash
   # Check your current IP
   curl ifconfig.me
   
   # Update security group to allow your IP
   # Edit terraform.tfvars and run: terraform apply
   ```

3. **Wrong SSH key:**
   ```bash
   # Verify key fingerprint
   ssh-keygen -l -f ~/.ssh/verifact-key.pub
   
   # Check AWS key pair fingerprint
   aws ec2 describe-key-pairs --key-names verifact-key --region ap-south-1
   ```

### Issue: "Docker login failed"

**Solution:**
```bash
# Login manually
docker login

# Enter Docker Hub credentials
# Then retry deployment
./deploy.sh
```

### Issue: "Health check failed"

**Check backend logs:**
```bash
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 \
  'cd /app && sudo docker logs verifact-backend --tail 50'
```

**Common causes:**
- Redis connection failed → Check Redis container
- API key issues → Verify SSM parameters
- Port already in use → Restart Docker

**Fix and redeploy:**
```bash
# Fix the issue in code
vim src/api/main.py

# Redeploy
./deploy.sh
```

### Issue: "Buildx not available"

**Solution:**
```bash
# Update Docker Desktop to latest version
# Or install buildx plugin:
docker buildx install

# Verify
docker buildx version
```

---

## 🔄 Rollback to Previous Version

If deployment fails or introduces issues:

### Method 1: Deploy Previous Image Tag

```bash
# If you tagged previous version
VERSION=v1.4.0 ./deploy.sh
```

### Method 2: Manual Rollback on EC2

```bash
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204

cd /app

# List available images
sudo docker images | grep ai-league-codesurgeons

# Update docker-compose.yml to use previous image
sudo vim docker-compose.yml
# Change: image: kickdrishu/ai-league-codesurgeons:latest
# To:     image: kickdrishu/ai-league-codesurgeons:SHA_OR_TAG

# Restart
sudo docker-compose up -d backend
```

### Method 3: Revert Code and Redeploy

```bash
# Revert to previous commit
git log --oneline
git revert <commit-hash>

# Redeploy
./deploy.sh
```

---

## 📊 Monitoring Deployment

### Watch Logs During Deployment

```bash
# In another terminal while deploy.sh runs
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 \
  'cd /app && sudo docker logs -f verifact-backend'
```

### Check Container Status

```bash
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 \
  'cd /app && sudo docker-compose ps'
```

### Monitor Resource Usage

```bash
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 \
  'sudo docker stats verifact-backend --no-stream'
```

---

## 🔐 Security Best Practices

### 1. Protect SSH Key

```bash
# Correct permissions
chmod 400 ~/.ssh/verifact-key

# Never commit to git
# Already in .gitignore
```

### 2. Use Environment-Specific Keys

```bash
# Different keys for different environments
SSH_KEY=~/.ssh/dev-key.pem EC2_HOST=dev.example.com ./deploy.sh
SSH_KEY=~/.ssh/prod-key.pem EC2_HOST=prod.example.com ./deploy.sh
```

### 3. Tag Production Deployments

```bash
# Use semantic versioning for production
VERSION=v1.0.0 EC2_HOST=production-ip ./deploy.sh

# Keep latest for development
./deploy.sh  # Uses :latest tag
```

---

## ⚡ Performance Tips

### Faster Builds

The script uses Docker layer caching automatically. To maximize:

1. **Don't change requirements.txt often** - It's near the top of Dockerfile
2. **Use .dockerignore** - Exclude unnecessary files
3. **Keep buildx builder running** - Script reuses existing builder

### Faster Deployments

Zero-downtime deployment is automatic:
1. New container starts while old one runs
2. Health check ensures new container is ready
3. Old container stops only after new one is healthy

---

## 📁 Related Files

- **Build Script:** [`build-and-push.sh`](build-and-push.sh) - Docker image only
- **Deploy Script:** [`deploy.sh`](deploy.sh) - Full deployment (this script)
- **Dockerfile:** [`Dockerfile`](Dockerfile) - Container definition
- **Deployment Info:** [`../DEPLOYMENT_INFO.md`](../DEPLOYMENT_INFO.md) - Infrastructure details

---

## 🔗 Additional Resources

- **Docker Hub Repository:** https://hub.docker.com/r/kickdrishu/ai-league-codesurgeons
- **Backend README:** [`README.md`](README.md)
- **Infrastructure README:** [`../infra/README.md`](../infra/README.md)

---

## 💡 Tips & Tricks

### Alias for Quick Deployment

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
alias verifact-deploy='cd /Users/apple/Developer/KD/ai-league/week-1/backend && ./deploy.sh'
alias verifact-deploy-dry='cd /Users/apple/Developer/KD/ai-league/week-1/backend && ./deploy.sh --dry-run'
```

Then deploy from anywhere:
```bash
verifact-deploy
```

### Deployment Notifications

Add to the end of your deployment command:

```bash
# macOS notification
./deploy.sh && osascript -e 'display notification "Deployment successful" with title "VeriFact"'

# Slack notification (if webhook configured)
./deploy.sh && curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"VeriFact deployed successfully"}' \
  YOUR_SLACK_WEBHOOK_URL
```

### Continuous Deployment

For automatic deployments on git push, see CI/CD section in main README.

---

**Last Updated:** February 15, 2026  
**Script Version:** 1.0.0  
**Maintained By:** CodeSurgeons Team
