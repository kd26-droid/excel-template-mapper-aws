# GitHub Repository Setup Guide

## 🚀 Preparing for GitHub & Amplify Deployment

This guide walks you through setting up your GitHub repository and connecting it with AWS Amplify for automatic deployments.

---

## ⚠️ CRITICAL SECURITY REMINDER

**NEVER commit AWS credentials to GitHub!** The credentials you shared earlier are compromised and must be rotated immediately.

### 🔒 Security Checklist Before Pushing to GitHub:

1. **Rotate AWS Credentials**:
   ```bash
   # Delete compromised keys
   aws iam delete-access-key --access-key-id AKIAZVHK6XPIQ4PT23MC --user-name YOUR_USERNAME
   
   # Create new keys
   aws iam create-access-key --user-name YOUR_USERNAME
   ```

2. **Verify .gitignore**:
   - ✅ `.env` files excluded
   - ✅ AWS credentials excluded  
   - ✅ Temporary files excluded
   - ✅ Build artifacts excluded

---

## 📁 Repository Structure Ready for GitHub

```
excel-template-mapper-final/
├── .gitignore                     # ✅ Comprehensive exclusions
├── README.md                      # ✅ Complete documentation
├── DEPLOYMENT_LOG.md              # ✅ Deployment progress
├── GITHUB_SETUP.md               # ✅ This guide
├── 
├── amplify/                       # ✅ Amplify configuration
│   ├── backend/                   
│   │   ├── function/excelMapper/  # ✅ Lambda function
│   │   ├── api/excelMapperAPI/    # ✅ API Gateway config
│   │   └── storage/               # ✅ S3 & DynamoDB config
│   ├── cli.json                   # ✅ Amplify CLI settings
│   └── .gitignore                 # ✅ Amplify-specific exclusions
│
├── infrastructure/                # ✅ AWS Infrastructure
│   ├── cloudformation-template.yaml  # ✅ Complete infrastructure
│   ├── cloudwatch-dashboard.json     # ✅ Monitoring dashboard
│   ├── cloudwatch-alarms.yaml        # ✅ Alert configuration
│   ├── s3-cors-config.json          # ✅ CORS settings
│   ├── dynamodb-tables.sql          # ✅ Database schema
│   ├── deploy.sh                     # ✅ Deployment script
│   ├── test-deployment.sh           # ✅ Testing script
│   └── lambda-deployment-package.sh # ✅ Lambda build script
│
├── frontend/                      # ✅ React application
│   ├── src/
│   │   ├── services/api.js        # ✅ Updated for Amplify
│   │   └── [other components]
│   ├── .env.example               # ✅ Environment template
│   └── package.json               # ✅ Dependencies
│
└── lambda.py                      # ✅ Original reference
```

---

## 📝 Step-by-Step GitHub Setup

### 1. Initialize Git Repository

```bash
cd /path/to/excel-template-mapper-final

# Initialize git if not already done
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Complete Excel Template Mapper with AWS infrastructure

- Added comprehensive Lambda function for Excel processing
- CloudFormation templates for full AWS infrastructure  
- S3 buckets with CORS configuration
- DynamoDB tables with proper schema
- CloudWatch monitoring and alerting
- Amplify configuration for serverless deployment
- Complete frontend React application
- Deployment and testing scripts

🚀 Ready for AWS Amplify deployment"
```

### 2. Create GitHub Repository

#### Option A: Using GitHub CLI (Recommended)
```bash
# Install GitHub CLI if not installed
# macOS: brew install gh
# Windows: winget install GitHub.cli

# Login to GitHub
gh auth login

# Create repository
gh repo create excel-template-mapper --public --description "AI-powered Excel template mapper with serverless AWS architecture"

# Add remote
git remote add origin https://github.com/YOUR_USERNAME/excel-template-mapper.git

# Push to GitHub
git branch -M main
git push -u origin main
```

#### Option B: Manual GitHub Creation
1. Go to [GitHub.com](https://github.com)
2. Click "New Repository"
3. Repository name: `excel-template-mapper`
4. Description: `AI-powered Excel template mapper with serverless AWS architecture`
5. Make it **Public** (for Amplify free tier)
6. Don't initialize with README (we have one)
7. Click "Create Repository"

```bash
# Add remote and push
git remote add origin https://github.com/YOUR_USERNAME/excel-template-mapper.git
git branch -M main
git push -u origin main
```

### 3. Verify GitHub Repository

✅ **Check that these files are present:**
- `README.md` with complete documentation
- `DEPLOYMENT_LOG.md` with progress tracking
- `amplify/` directory with full configuration
- `infrastructure/` with CloudFormation templates
- `frontend/` with React application
- `.gitignore` properly excluding sensitive files

❌ **Ensure these are NOT present:**
- `.env` files with credentials
- `aws-exports.js` 
- Any files with actual AWS credentials
- Large binary files or build artifacts

---

## 🔗 Connecting to AWS Amplify

### 1. Access AWS Amplify Console

1. Open [AWS Amplify Console](https://console.aws.amazon.com/amplify/)
2. Ensure you're in the correct region (us-east-1)
3. Click "New App" → "Host web app"

### 2. Connect GitHub Repository

1. **Select GitHub** as source
2. **Authenticate** with GitHub (if needed)
3. **Select Repository**: `excel-template-mapper`
4. **Select Branch**: `main`
5. Click "Next"

### 3. Configure Build Settings

Amplify should auto-detect the configuration. Verify:

```yaml
version: 1
backend:
  phases:
    build:
      commands:
        - amplifyPush --simple
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - npm ci
    build:
      commands:
        - npm run build
  artifacts:
    baseDirectory: frontend/build
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
```

### 4. Configure Environment Variables

In Amplify Console, go to **Environment Variables**:

```
REACT_APP_AWS_REGION=us-east-1
NODE_ENV=production
```

### 5. Advanced Settings

- **Build Image**: Amazon Linux:2023
- **Live Package Updates**: Enabled
- **Node.js Version**: 18 (latest LTS)
- **Python Version**: 3.9

### 6. Deploy Application

1. Click "Save and Deploy"
2. Amplify will automatically:
   - Pull code from GitHub
   - Deploy backend infrastructure
   - Build and deploy frontend
   - Configure CI/CD pipeline

---

## 📊 Post-Deployment Verification

### 1. Check Amplify Deployment

In Amplify Console, verify all phases pass:
- ✅ **Provision**: Backend infrastructure created
- ✅ **Build**: Frontend build successful  
- ✅ **Deploy**: Application deployed
- ✅ **Verify**: Health checks pass

### 2. Test Application

1. **Open Amplify URL**: https://main.xxxxx.amplifyapp.com
2. **Test File Upload**: Upload sample Excel files
3. **Test Mapping**: Verify AI suggestions work
4. **Test Download**: Confirm processed files download
5. **Test Templates**: Save and load mapping templates

### 3. Monitor Infrastructure

1. **CloudWatch Dashboard**: Monitor Lambda, API Gateway, DynamoDB
2. **CloudWatch Alarms**: Verify alert notifications  
3. **S3 Buckets**: Confirm file uploads/downloads
4. **DynamoDB**: Check session and template data

---

## 🔄 Continuous Deployment Setup

### Automatic Deployments

Amplify automatically deploys when you push to `main`:

```bash
# Make changes
git add .
git commit -m "feat: add new Excel processing feature"
git push origin main

# Amplify automatically:
# 1. Detects GitHub push
# 2. Pulls latest code
# 3. Runs backend deployment
# 4. Builds frontend
# 5. Deploys to production
```

### Branch-Based Deployments

Set up feature branches for development:

```bash
# Create feature branch
git checkout -b feature/new-mapping-algorithm

# Make changes and push
git push origin feature/new-mapping-algorithm

# In Amplify Console:
# 1. Connect branch for preview deployments
# 2. Test changes in isolation
# 3. Merge to main when ready
```

---

## 🚨 Security Best Practices

### 1. Environment Variables
- ✅ Use Amplify Environment Variables for configuration
- ❌ Never hardcode API keys or credentials
- ✅ Use different environments (dev/staging/prod)

### 2. Access Control
- ✅ Enable Amplify Access Control if needed
- ✅ Set up CloudFront for CDN and DDoS protection
- ✅ Configure WAF rules for API protection

### 3. Monitoring
- ✅ Set up CloudWatch alarms
- ✅ Enable AWS CloudTrail logging
- ✅ Configure SNS notifications for alerts

### 4. Backup Strategy
- ✅ Enable DynamoDB point-in-time recovery
- ✅ Configure S3 versioning and lifecycle policies
- ✅ Regular infrastructure backups with CloudFormation

---

## 📈 Scaling Considerations

### Performance Optimization

1. **Lambda**: Monitor cold starts, adjust memory allocation
2. **DynamoDB**: Monitor capacity and optimize indexes
3. **S3**: Enable Transfer Acceleration for large files
4. **CloudFront**: Add CDN for static assets

### Cost Optimization

1. **DynamoDB**: Use pay-per-request for variable workloads
2. **S3**: Implement lifecycle policies for old files
3. **Lambda**: Optimize function memory and timeout
4. **CloudWatch**: Adjust log retention periods

---

## 🛠️ Development Workflow

### Local Development

```bash
# 1. Clone repository
git clone https://github.com/YOUR_USERNAME/excel-template-mapper.git
cd excel-template-mapper

# 2. Setup frontend
cd frontend
npm install
cp .env.example .env
# Edit .env with your API endpoints

# 3. Start development server
npm start

# 4. For backend changes
cd ../infrastructure
./deploy.sh  # Deploy to AWS
./test-deployment.sh  # Validate deployment
```

### Production Deployment

```bash
# 1. Test changes locally
npm run build
npm test

# 2. Deploy to staging branch
git checkout -b staging
git push origin staging

# 3. Test staging environment
# Access: https://staging.xxxxx.amplifyapp.com

# 4. Deploy to production
git checkout main
git merge staging
git push origin main
```

---

## 📞 Support & Troubleshooting

### Common Issues

1. **Build Failures**:
   - Check Amplify build logs
   - Verify Node.js/Python versions
   - Check environment variables

2. **API Errors**:
   - Check Lambda function logs in CloudWatch
   - Verify API Gateway configuration
   - Test endpoints with Postman/curl

3. **File Upload Issues**:
   - Check S3 CORS configuration
   - Verify bucket permissions
   - Monitor S3 access logs

### Getting Help

- **AWS Documentation**: [Amplify Docs](https://docs.amplify.aws/)
- **CloudWatch Logs**: Monitor application logs
- **AWS Support**: Use AWS Support Center
- **Community**: AWS Amplify Discord/Forums

---

## ✅ Final Checklist

### Before Pushing to GitHub:
- [ ] AWS credentials rotated and secured
- [ ] .gitignore comprehensive and tested
- [ ] README.md documentation complete
- [ ] Environment variables externalized
- [ ] No hardcoded secrets in code

### After GitHub Setup:
- [ ] Repository created and pushed
- [ ] Amplify app connected and deployed
- [ ] Custom domain configured (optional)
- [ ] Monitoring and alerts configured
- [ ] End-to-end testing completed

### Production Ready:
- [ ] Performance baseline established
- [ ] Security review completed
- [ ] Backup strategy implemented
- [ ] Monitoring dashboards configured
- [ ] Team access permissions set

---

**🎉 Your Excel Template Mapper is now ready for GitHub and AWS Amplify!**

Once you complete these steps, you'll have a fully automated CI/CD pipeline with:
- ✅ Serverless AWS infrastructure
- ✅ Automatic deployments from GitHub
- ✅ Comprehensive monitoring and alerting
- ✅ Scalable and secure architecture
- ✅ Professional development workflow

**Next Steps**: Push to GitHub and connect with Amplify to go live! 🚀