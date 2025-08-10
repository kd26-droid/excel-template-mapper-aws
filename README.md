# Excel Template Mapper - AWS Amplify Edition

A powerful web application that uses AI to map Excel files to templates, built on AWS Amplify with serverless architecture.

## 🚀 Features

- **AI-Powered Header Mapping**: Intelligent column mapping using fuzzy matching and semantic understanding
- **Template System**: Save and reuse mapping configurations
- **Formula Builder**: Create dynamic tags and specification columns
- **Real-time Processing**: Lambda-based backend for scalable file processing
- **Secure File Storage**: S3 integration for reliable file management
- **Modern UI**: React-based frontend with responsive design

## 🏗️ Architecture

- **Frontend**: React.js application hosted on Amplify
- **Backend**: AWS Lambda functions with Python runtime
- **Storage**: Amazon S3 for file storage, DynamoDB for session/template management
- **API**: REST API via API Gateway
- **Infrastructure**: Managed through AWS Amplify CLI

## 🛠️ Prerequisites

- Node.js (v14 or later)
- AWS CLI configured with appropriate permissions
- Amplify CLI installed globally: `npm install -g @aws-amplify/cli`

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd excel-template-mapper-final
   ```

2. **Install frontend dependencies**
   ```bash
   cd frontend
   npm install
   ```

3. **Configure Amplify**
   ```bash
   amplify configure
   amplify init
   ```

4. **Deploy backend resources**
   ```bash
   amplify push
   ```

5. **Set up environment variables**
   ```bash
   cp frontend/.env.example frontend/.env
   # Update the API_BASE_URL with your Amplify API endpoint
   ```

## 🚀 Deployment

### Local Development

```bash
# Start frontend development server
cd frontend
npm start

# The app will be available at http://localhost:3000
```

### Production Deployment

```bash
# Deploy to Amplify
amplify publish
```

## 📁 Project Structure

```
excel-template-mapper-final/
├── amplify/                    # Amplify configuration
│   ├── backend/
│   │   ├── function/
│   │   │   └── excelMapper/    # Lambda function
│   │   ├── api/                # API Gateway configuration
│   │   └── storage/            # S3 and DynamoDB configuration
│   └── .config/
├── frontend/                   # React application
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/           # API integration
│   │   └── utils/
│   └── public/
├── lambda.py                   # Original Lambda function (reference)
└── README.md
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the frontend directory:

```env
REACT_APP_API_BASE_URL=https://your-api-id.execute-api.us-east-1.amazonaws.com/prod
REACT_APP_AWS_REGION=us-east-1
```

### AWS Resources

The application creates the following AWS resources:

- **Lambda Function**: `excelMapper` - Handles all backend operations
- **API Gateway**: REST API with CORS enabled
- **S3 Bucket**: File storage for uploads and processed files
- **DynamoDB Tables**:
  - `ExcelMapper_Sessions` - Session management
  - `ExcelMapper_Templates` - Template storage
  - `ExcelMapper_TagTemplates` - Tag template storage
  - `ExcelMapper_ProcessingJobs` - Job tracking

## 🔄 API Endpoints

- `POST /upload` - Upload files
- `GET /headers/{session_id}` - Get file headers
- `POST /mapping` - Get mapping suggestions
- `POST /mapping/save` - Save column mappings
- `GET /data` - Get transformed data
- `POST /download` - Generate download links
- `GET /templates` - List saved templates
- `POST /templates/save` - Save new template
- `POST /formulas/apply` - Apply formula rules
- `POST /create-factwise-id` - Create Factwise ID column

## 🔒 Security

- CORS configured for cross-origin requests
- Input validation and sanitization
- Temporary file cleanup
- Session-based access control
- S3 presigned URLs for secure downloads

## 📊 Monitoring

Monitor your application using:

- AWS CloudWatch Logs for Lambda function logs
- API Gateway metrics for API performance
- S3 access logs for file operations
- DynamoDB metrics for database operations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:

1. Check the AWS Amplify documentation
2. Review CloudWatch logs for errors
3. Ensure all AWS permissions are correctly configured
4. Verify environment variables are set

## 🔄 Updates and Maintenance

To update the application:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
cd frontend && npm update

# Deploy changes
amplify push
```

## 📈 Performance Tips

1. **Lambda Optimization**: Increase memory allocation for large files
2. **S3 Configuration**: Enable transfer acceleration if needed
3. **DynamoDB**: Consider provisioned capacity for high traffic
4. **Caching**: Implement CloudFront for static assets

---

Built with ❤️ using AWS Amplify and serverless technologies.