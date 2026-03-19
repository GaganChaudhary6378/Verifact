# VeriFact Backend - Deployment Information

**Deployment Date:** February 15, 2026  
**Environment:** Development  
**Region:** ap-south-1 (Mumbai, India)

---

## 🚀 Deployment Status

✅ **SUCCESSFULLY DEPLOYED**

All services are running and healthy.

---

## 📡 Access Information

### Public Endpoints

| Service | URL |
|---------|-----|
| **API Base URL** | http://43.205.75.204:8000 |
| **API Documentation (Swagger)** | http://43.205.75.204:8000/docs |
| **Health Check** | http://43.205.75.204:8000/health |
| **WebSocket Endpoint** | ws://43.205.75.204:8000/api/v1/ws/verify/{user_id} |

### SSH Access

```bash
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204
```

**SSH Key Location:** `~/.ssh/verifact-key` (local machine)  
**Note:** The SSH private key is stored locally on your machine and is **not** committed to git.

---

## 🏗️ Infrastructure Details

### AWS Resources

| Resource | Details |
|----------|---------|
| **Instance ID** | i-0a32d41f315ed7a4a |
| **Instance Type** | t3.medium (2 vCPU, 4GB RAM) |
| **Public IP** | 43.205.75.204 (Elastic IP) |
| **Private IP** | 172.31.23.149 |
| **AMI** | Amazon Linux 2023 (ami-02a8bcaaf6d87b759) |
| **Security Group** | sg-001ae91b8e255756a |

### Encryption

| Component | Encryption Method |
|-----------|-------------------|
| **EBS Volume** | AWS KMS (Customer Managed Key) |
| **KMS Key ID** | 005ecc20-a69f-4336-9dde-72dd8c55fc4b |
| **KMS Key ARN** | arn:aws:kms:ap-south-1:503226040441:key/005ecc20-a69f-4336-9dde-72dd8c55fc4b |
| **KMS Alias** | alias/verifact-ebs-dev |
| **API Keys** | AWS Systems Manager Parameter Store (SecureString) |

### Storage

- **EBS Volume:** 30 GB GP3 (encrypted with KMS)
- **Redis Data Volume:** Docker volume (app_redis-data)

---

## 🐳 Docker Configuration

### Deployed Image

```
gagan/ai:latest
```

**Image Registry:** Docker Hub  
**Architecture:** Multi-arch (amd64/arm64)

### Running Containers

| Container | Image | Ports |
|-----------|-------|-------|
| **verifact-backend** | gagan/ai:latest | 8000:8000 |
| **verifact-redis-stack** | redis/redis-stack-server:latest | 6379:6379 |

---

## 🔑 Configuration

### Environment Variables

Environment variables are stored in `/app/.env` on the EC2 instance, populated from AWS Systems Manager Parameter Store:

- `OPENAI_API_KEY` - OpenAI API key (embeddings and LLM)
- `EXA_API_KEY` - Exa API key (web search)
- `COHERE_API_KEY` - Cohere API key (reranking)
- `NEWS_API_KEY` - News API key (news articles)
- `REDIS_PASSWORD` - Redis authentication password
- `PRIMARY_LLM` - gpt-4o-mini
- `FALLBACK_LLM` - gpt-4o

### Security Groups

**Inbound Rules:**
- Port 22 (SSH): 0.0.0.0/0
- Port 8000 (API): 0.0.0.0/0

**Outbound Rules:**
- All traffic allowed

---

## 🔧 Management Commands

### Access the Instance

```bash
# SSH into the instance
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204

# Once connected, navigate to app directory
cd /app
```

### Docker Management

```bash
# View running containers
sudo docker-compose ps

# View logs (backend)
sudo docker logs verifact-backend
sudo docker logs -f verifact-backend  # Follow logs

# View logs (Redis)
sudo docker logs verifact-redis-stack

# Restart services
sudo docker-compose restart

# Stop services
sudo docker-compose down

# Start services
sudo docker-compose up -d

# Pull latest image and restart
sudo docker-compose pull
sudo docker-compose up -d
```

### Update Deployment

```bash
# On your local machine:
cd /Users/apple/Developer/KD/ai-league/week-1/backend

# Build and push new image
export DOCKER_USERNAME=gagan
export IMAGE_NAME=ai
./build-and-push.sh

# On EC2 instance:
cd /app
sudo docker-compose pull
sudo docker-compose up -d
```

### View System Logs

```bash
# User data script log (initial setup)
sudo cat /var/log/user-data.log

# Docker service logs
sudo journalctl -u docker

# System logs
sudo journalctl -xe
```

---

## 🔍 Health Check

Test the deployment health:

```bash
# From your local machine
curl http://43.205.75.204:8000/health

# Expected response:
{
  "status": "healthy",
  "service": "verifact",
  "version": "1.0.0",
  "components": {
    "redis": "connected",
    "llm": "ready",
    "embeddings": "ready"
  }
}
```

---

## 💰 Cost Estimate

**Monthly AWS Costs (ap-south-1 region):**

| Item | Cost |
|------|------|
| EC2 t3.medium (on-demand, 24/7) | ~$30/month |
| EBS 30GB GP3 | ~$3/month |
| Elastic IP (while instance running) | Free |
| KMS (single key, <20k requests/month) | Free |
| SSM Parameter Store (Standard) | Free |
| Data Transfer (estimated) | Varies |
| **Total** | **~$33/month** |

**Cost Optimization Options:**
- Use Reserved Instances (save ~40%)
- Use Spot Instances for dev (save ~70%)
- Stop instance during off-hours (pay only for storage)

---

## 📝 Terraform Management

### View Infrastructure

```bash
cd /Users/apple/Developer/KD/ai-league/week-1/infra

# Show current state
terraform show

# List resources
terraform state list

# View outputs
terraform output
```

### Update Infrastructure

```bash
# Preview changes
terraform plan

# Apply changes
terraform apply

# Destroy everything
terraform destroy
```

---

## 🔒 Security Notes

### Implemented Security Measures

✅ EBS volumes encrypted with AWS KMS  
✅ KMS key rotation enabled  
✅ API keys stored in AWS Systems Manager Parameter Store (encrypted)  
✅ Redis password protected  
✅ Docker containers run as non-root user  
✅ IAM role with least-privilege access  
✅ Security group configured for required ports only  

### Recommendations for Production

⚠️ **Important:** Current configuration is for **development only**. For production:

1. **Restrict SSH Access:**
   ```bash
   # Edit terraform.tfvars
   allowed_ssh_cidr = "YOUR_IP/32"
   terraform apply
   ```

2. **Add HTTPS/SSL:**
   - Set up a domain name
   - Install nginx as reverse proxy
   - Configure Let's Encrypt SSL certificate

3. **Enable Monitoring:**
   - Configure CloudWatch alarms
   - Set up log aggregation
   - Enable detailed monitoring

4. **Backup Strategy:**
   - Schedule EBS snapshots
   - Back up Redis data volume
   - Store backups in S3

5. **Update Passwords:**
   - Change `redis_password` to a strong value
   - Update SSM parameters:
   ```bash
   aws ssm put-parameter \
     --name /verifact/dev/redis_password \
     --value "NEW_STRONG_PASSWORD" \
     --type SecureString \
     --overwrite \
     --region ap-south-1
   ```

---

## 📚 Additional Resources

- **Backend README:** `/Users/apple/Developer/KD/ai-league/week-1/backend/README.md`
- **Infrastructure README:** `/Users/apple/Developer/KD/ai-league/week-1/infra/README.md`
- **Docker Hub Repository:** https://hub.docker.com/r/gagan/ai

---

## 🆘 Troubleshooting

### Common Issues

**Issue: Health check fails**
```bash
# Check if containers are running
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 'cd /app && sudo docker-compose ps'

# Check backend logs
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 'cd /app && sudo docker logs verifact-backend --tail 50'

# Restart services
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 'cd /app && sudo docker-compose restart'
```

**Issue: Can't SSH into instance**
```bash
# Verify key permissions
chmod 400 ~/.ssh/verifact-key

# Check security group allows your IP
aws ec2 describe-security-groups --group-ids sg-001ae91b8e255756a --region ap-south-1
```

**Issue: Redis connection errors**
```bash
# Verify Redis is running
ssh -i ~/.ssh/verifact-key ec2-user@43.205.75.204 'sudo docker exec verifact-redis-stack redis-cli --pass verifact_redis_pass_CHANGE_ME ping'

# Expected: PONG
```

---

**Last Updated:** February 15, 2026  
**Maintained By:** CodeSurgeons Team
