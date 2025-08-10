# AWS Amplify Migration Guide: Django to Lambda + S3

This guide provides a comprehensive list of files to upload to Claude for converting the Django backend to a robust AWS Lambda function with S3 storage.

## Architecture Overview

**Target Architecture:**
- **Frontend**: AWS Amplify (React app)
- **Backend**: AWS Lambda functions (serverless)
- **Storage**: AWS S3 (file uploads and processing)
- **Database**: DynamoDB (replacing SQLite)
- **No API Gateway**: Direct Lambda function URLs or Amplify API integration

## Files to Upload to Claude

### 1. Backend Core Files

#### Django Application Files
```
backend/excel_mapper/models.py
backend/excel_mapper/views.py
backend/excel_mapper/bom_header_mapper.py
backend/excel_mapper/urls.py
```

#### Django Configuration
```
backend/excel_mapping/settings.py
backend/excel_mapping/urls.py
backend/requirements.txt
```

#### Database Migrations (for DynamoDB schema design)
```
backend/excel_mapper/migrations/0001_initial.py
backend/excel_mapper/migrations/0002_add_formula_rules.py
backend/excel_mapper/migrations/0003_add_tag_template.py
backend/excel_mapper/migrations/0004_add_factwise_rules.py
backend/excel_mapper/migrations/0005_mappingtemplate_default_values.py
backend/excel_mapper/migrations/0006_add_default_templates.py
```

### 2. Frontend Integration Files

#### API Integration
```
frontend/src/services/api.js
frontend/src/hooks/useApi.js
frontend/src/constants/index.js
```

#### Main Components (for understanding API calls)
```
frontend/src/pages/Dashboard.js
frontend/src/pages/UploadFiles.js
frontend/src/pages/ColumnMapping.js
frontend/src/pages/DataEditor.js
```

### 3. Configuration Files

#### Package Configuration
```
frontend/package.json
backend/gunicorn.conf.py
```

## Conversion Requirements

### Lambda Function Structure Needed

1. **File Upload Handler**
   - Replace Django file upload with S3 direct upload
   - Generate presigned URLs for secure uploads
   - Process Excel/CSV files using pandas

2. **Template Management**
   - Convert Django models to DynamoDB tables
   - CRUD operations for mapping templates
   - Tag template management

3. **Data Processing**
   - Excel to Excel mapping logic
   - Formula application
   - BOM header mapping functionality

4. **Session Management**
   - Replace in-memory sessions with DynamoDB
   - Stateless Lambda functions
   - S3 for temporary file storage

### Key Conversion Points

#### From Django Views to Lambda Functions:
- `@api_view` decorators → Lambda handlers
- Django ORM → DynamoDB operations
- File uploads → S3 operations
- Session management → DynamoDB sessions

#### Database Migration:
- SQLite → DynamoDB
- Django models → DynamoDB table schemas
- Foreign keys → DynamoDB relationships

#### File Storage:
- Local file system → S3 buckets
- Temporary files → S3 with lifecycle policies
- Media files → S3 with CloudFront

## Expected Lambda Functions

### 1. File Management Functions
- `upload_handler` - Handle file uploads to S3
- `file_processor` - Process uploaded Excel/CSV files
- `download_handler` - Generate download URLs

### 2. Template Management Functions
- `template_crud` - Create, read, update, delete templates
- `tag_template_crud` - Manage tag templates
- `default_templates` - Initialize default templates

### 3. Data Processing Functions
- `column_mapping` - Handle column mapping logic
- `data_transformation` - Apply formulas and transformations
- `bom_processing` - BOM header mapping

### 4. System Functions
- `health_check` - System diagnostics
- `session_manager` - Handle user sessions

## Frontend Changes Required

### API Endpoint Updates
Update `frontend/src/services/api.js` to use:
- Lambda function URLs instead of Django URLs
- S3 presigned URLs for file operations
- DynamoDB session management

### Environment Configuration
```javascript
// Replace Django backend URLs with Lambda endpoints
const API_BASE_URL = process.env.REACT_APP_API_URL || 'https://lambda-function-url.amazonaws.com'
```

## AWS Resources Needed

### S3 Buckets
- `excel-mapper-uploads` - User file uploads
- `excel-mapper-processed` - Processed files
- `excel-mapper-templates` - Template files

### DynamoDB Tables
- `ExcelMapper_Sessions` - User sessions
- `ExcelMapper_Templates` - Mapping templates
- `ExcelMapper_TagTemplates` - Tag templates
- `ExcelMapper_ProcessingJobs` - Background jobs

### Lambda Functions
- Runtime: Python 3.9+
- Memory: 512MB - 3GB (depending on file processing needs)
- Timeout: 15 minutes (for large file processing)
- Layers: pandas, openpyxl, xlrd dependencies

## Deployment Strategy

### Phase 1: Backend Migration
1. Convert Django views to Lambda functions
2. Set up DynamoDB tables
3. Configure S3 buckets
4. Test Lambda functions individually

### Phase 2: Frontend Integration
1. Update API calls in React app
2. Deploy to AWS Amplify
3. Configure environment variables
4. Test end-to-end functionality

### Phase 3: Optimization
1. Add error handling and retries
2. Implement caching strategies
3. Set up monitoring and logging
4. Performance optimization

## Security Considerations

### IAM Roles
- Lambda execution role with S3, DynamoDB permissions
- S3 bucket policies for secure access
- CORS configuration for frontend integration

### Data Protection
- Encrypt S3 objects at rest
- Use VPC endpoints for DynamoDB access
- Implement request signing for API security

## Cost Optimization

### Lambda
- Use appropriate memory allocation
- Implement connection pooling
- Cache frequently accessed data

### S3
- Lifecycle policies for temporary files
- Intelligent tiering for long-term storage
- CloudFront for static assets

### DynamoDB
- On-demand billing for variable workloads
- Global secondary indexes for query optimization
- TTL for temporary session data

## Instructions for Claude

When uploading these files to Claude, ask it to:

1. **Analyze the Django structure** and create equivalent Lambda functions
2. **Design DynamoDB schemas** based on Django models
3. **Create S3 integration** for file operations
4. **Implement session management** using DynamoDB
5. **Provide deployment scripts** for AWS resources
6. **Update frontend API calls** to work with Lambda
7. **Include error handling** and logging
8. **Create CloudFormation/CDK templates** for infrastructure

### Example Prompt for Claude:

"I need to convert this Django backend to AWS Lambda functions with S3 storage and DynamoDB. Please:

1. Convert each Django view to a Lambda function
2. Replace Django models with DynamoDB table schemas
3. Replace file uploads with S3 operations
4. Create session management using DynamoDB
5. Provide AWS CDK/CloudFormation templates
6. Update the frontend API calls accordingly
7. Include comprehensive error handling
8. Add monitoring and logging setup

The application is an Excel template mapper that processes Excel/CSV files and applies column mapping transformations."

## File Upload Order

Upload files in this order for best results:

1. **Core Models** - `models.py` first to understand data structure
2. **Main Views** - `views.py` for business logic
3. **URL Patterns** - `urls.py` for endpoint mapping
4. **Frontend API** - `api.js` for integration points
5. **Configuration** - `settings.py` and `requirements.txt`
6. **Supporting Files** - BOM mapper, migrations, etc.

This ensures Claude has the full context to create a robust, scalable Lambda-based solution.