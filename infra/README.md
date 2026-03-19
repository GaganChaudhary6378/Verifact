# VeriFact Infrastructure - Terraform Deployment

Automated EC2 deployment for VeriFact backend using Terraform, Docker, and Redis Stack.

## 🚀 Quick Start

### Prerequisites

1. **AWS Account** with CLI configured
2. **Terraform** installed (`brew install terraform`)
3. **Docker Hub account** with backend image pushed
4. **SSH Key Pair** created in AWS EC2

### One-Command Deployment

```bash
# 1. Configure variables
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# 2. Deploy everything
terraform init
terraform apply

# 3. Get connection info
terraform output
```

That's it! Your backend will be running on EC2 with Redis Stack.

---

## 📋 Detailed Setup Guide

### Step 1: Install Prerequisites

```bash
# Install AWS CLI
brew install awscli

# Install Terraform
brew install terraform

# Configure AWS credentials
aws configure
# Enter your AWS Access Key ID
# Enter your AWS Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### Step 2: Create SSH Key Pair

**Option A: Use existing key**
- If you already have an SSH key pair in AWS, note its name

**Option B: Create new key**
```bash
# In AWS Console:
# EC2 → Key Pairs → Create Key Pair
# Name: verifact-key
# Type: RSA
# Format: .pem
# Download and save to ~/.ssh/verifact-key.pem
chmod 400 ~/.ssh/verifact-key.pem
```

### Step 3: Build and Push Docker Image

```bash
# Navigate to backend directory
cd ../backend

# Build and push multi-architecture image
export DOCKER_USERNAME=your-dockerhub-username
./build-and-push.sh

# Verify on Docker Hub
# https://hub.docker.com/r/YOUR_USERNAME/verifact-backend
```

### Step 4: Configure Terraform Variables

```bash
cd ../infra

# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit with your values
nano terraform.tfvars
```

**Required variables:**
- `ssh_key_name`: Your AWS SSH key pair name
- `docker_image`: Your Docker Hub image (e.g., `username/verifact-backend:latest`)
- `openai_api_key`: OpenAI API key
- `anthropic_api_key`: Anthropic API key

**Recommended changes:**
- `allowed_ssh_cidr`: Restrict to your IP (find with `curl ifconfig.me`)
- `redis_password`: Change from default for production

### Step 5: Deploy Infrastructure

```bash
# Initialize Terraform
terraform init

# Preview changes
terraform plan

# Deploy (type 'yes' when prompted)
terraform apply
```

Deployment takes ~3-5 minutes. The user data script will:
1. Install Docker and Docker Compose
2. Pull your Docker image
3. Start backend + Redis Stack containers
4. Configure auto-restart on reboot

### Step 6: Verify Deployment

```bash
# Get outputs
terraform output

# Test health endpoint
curl http://$(terraform output -raw instance_public_ip):8000/health

# Should return: {"status":"healthy"}
```

**Access API documentation:**
```bash
# Get the URL
terraform output api_docs_url

# Open in browser
open $(terraform output -raw api_docs_url)
```

---

## 🔧 Configuration

### Instance Sizing

Edit `instance_type` in `terraform.tfvars`:

| Instance Type | vCPU | RAM | Use Case |
|---------------|------|-----|----------|
| `t3.small` | 2 | 2GB | Testing only (may struggle) |
| `t3.medium` | 2 | 4GB | **Recommended for dev/staging** |
| `t3.large` | 2 | 8GB | Production |
| `t3.xlarge` | 4 | 16GB | High traffic production |

### Security

**Restrict SSH access** (highly recommended):
```bash
# Find your IP
curl ifconfig.me

# Edit terraform.tfvars
allowed_ssh_cidr = "YOUR_IP/32"

# Apply changes
terraform apply
```

**Change Redis password:**
```bash
# Edit terraform.tfvars
redis_password = "your-secure-password-here"

# Apply changes
terraform apply
```

### Environment

Set `environment` variable for tagging:
- `dev` - Development
- `staging` - Staging
- `prod` - Production

---

## 📊 Monitoring & Logs

### SSH into Instance

```bash
# Use the SSH command from outputs
terraform output -raw ssh_command | bash

# Or manually
ssh -i ~/.ssh/your-key.pem ec2-user@$(terraform output -raw instance_public_ip)
```

### View Logs

```bash
# SSH into instance first, then:

# View all containers
docker ps

# Backend logs
docker logs verifact-backend

# Follow backend logs
docker logs -f verifact-backend

# Redis logs
docker logs verifact-redis-stack

# User data script log (bootstrap)
sudo cat /var/log/user-data.log
```

### Check Service Status

```bash
# SSH into instance first, then:

cd /app
docker-compose ps

# Restart services if needed
docker-compose restart

# Pull latest image and restart
docker-compose pull && docker-compose up -d
```

---

## 🔄 Updates & Maintenance

### Deploy New Version

```bash
# 1. Build and push new Docker image
cd ../backend
export DOCKER_USERNAME=your-username
export VERSION=v1.1.0
./build-and-push.sh

# 2. Update on EC2
ssh -i ~/.ssh/your-key.pem ec2-user@$(cd ../infra && terraform output -raw instance_public_ip)
cd /app
docker-compose pull
docker-compose up -d
exit
```

### Update Infrastructure

```bash
# Edit Terraform files (main.tf, variables.tf, etc.)

# Preview changes
terraform plan

# Apply changes
terraform apply
```

### OS Updates

```bash
# SSH into instance
ssh -i ~/.ssh/your-key.pem ec2-user@INSTANCE_IP

# Update packages
sudo yum update -y

# Reboot if kernel updated
sudo reboot
```

---

## 🗑️ Teardown

### Destroy All Resources

```bash
terraform destroy

# Type 'yes' when prompted
```

This will delete:
- EC2 instance
- Elastic IP
- Security group
- All associated resources

**Warning:** This is irreversible! Data will be lost unless you have backups.

---

## 🐛 Troubleshooting

### Issue: `terraform apply` fails with "InvalidKeyPair.NotFound"

**Solution:** The SSH key name doesn't exist in AWS.
```bash
# List available keys
aws ec2 describe-key-pairs --query 'KeyPairs[*].KeyName'

# Update terraform.tfvars with correct key name
```

### Issue: Health check fails after deployment

**Solution:** Wait 2-3 minutes for user data script to complete.
```bash
# Check user data script progress
ssh -i ~/.ssh/your-key.pem ec2-user@INSTANCE_IP
sudo tail -f /var/log/user-data.log
```

### Issue: Can't SSH into instance

**Solutions:**
1. Check security group allows your IP:
   ```bash
   # Get your current IP
   curl ifconfig.me
   
   # Update allowed_ssh_cidr in terraform.tfvars
   # Then: terraform apply
   ```

2. Verify key permissions:
   ```bash
   chmod 400 ~/.ssh/your-key.pem
   ```

3. Check you're using correct username (`ec2-user` for Amazon Linux):
   ```bash
   ssh -i ~/.ssh/your-key.pem ec2-user@INSTANCE_IP
   ```

### Issue: Docker containers not running

**Solution:** Check logs and restart:
```bash
ssh -i ~/.ssh/your-key.pem ec2-user@INSTANCE_IP
cd /app
docker-compose ps
docker-compose logs
docker-compose up -d
```

### Issue: Redis connection errors

**Solution:** Verify Redis is healthy:
```bash
docker exec verifact-redis-stack redis-cli --pass YOUR_REDIS_PASSWORD ping
# Should return: PONG

# Check Redis modules
docker exec verifact-redis-stack redis-cli --pass YOUR_REDIS_PASSWORD MODULE LIST
# Should show: search, ReJSON, timeseries, bf
```

---

## 📁 File Structure

```
infra/
├── main.tf                    # Main Terraform configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── user-data.sh              # EC2 bootstrap script
├── terraform.tfvars.example  # Example variables file
├── .gitignore                # Git ignore rules
└── README.md                 # This file
```

---

## 🔐 Security Best Practices

1. **Never commit `terraform.tfvars`** - Contains sensitive API keys
2. **Restrict SSH access** - Set `allowed_ssh_cidr` to your IP only
3. **Change default passwords** - Update `redis_password` for production
4. **Use AWS Secrets Manager** - For production, store API keys in Secrets Manager
5. **Enable HTTPS** - Add nginx reverse proxy with Let's Encrypt SSL
6. **Regular updates** - Keep OS and Docker images updated
7. **Enable CloudWatch** - Monitor instance metrics and set up alarms

---

## 💰 Cost Estimate

**Monthly costs (us-east-1):**
- EC2 t3.medium (on-demand): ~$30/month
- Elastic IP (while instance running): Free
- EBS storage (30GB): ~$3/month
- Data transfer: Varies

**Total: ~$33/month** for dev/staging

**Cost optimization:**
- Use Reserved Instances for production (save ~40%)
- Use Spot Instances for dev (save ~70%)
- Stop instance during off-hours for dev

---

## 📚 Additional Resources

- [Terraform AWS Provider Docs](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [AWS EC2 Pricing](https://aws.amazon.com/ec2/pricing/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Redis Stack Documentation](https://redis.io/docs/stack/)

---

## 🆘 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Terraform and Docker logs
3. Consult the backend README: `../backend/README.md`

---

**Built with ❤️ using Terraform, Docker, and AWS**
