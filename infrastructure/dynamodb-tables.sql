-- Excel Template Mapper - DynamoDB Table Definitions
-- Note: This is SQL-like syntax for documentation. 
-- Actual DynamoDB tables are created via CloudFormation or AWS CLI

-- ========================================
-- Sessions Table
-- ========================================
TABLE: ExcelMapper_Sessions
PRIMARY KEY: session_id (String)
TTL ATTRIBUTE: ttl

ATTRIBUTES:
- session_id: String (Primary Key) - Unique session identifier
- created_at: String - ISO timestamp when session was created
- updated_at: String - ISO timestamp of last update
- ttl: Number - Unix timestamp for TTL expiration (24 hours)
- client_s3_key: String - S3 key for uploaded client file
- template_s3_key: String - S3 key for uploaded template file
- client_filename: String - Original client filename
- template_filename: String - Original template filename
- sheet_name: String - Selected sheet name from client file
- header_row: Number - Header row number (1-based)
- template_sheet_name: String - Selected template sheet name
- template_header_row: Number - Template header row number
- mappings: Map - Column mapping configuration
- formula_rules: List - Applied formula rules
- factwise_rules: List - Factwise ID generation rules
- default_values: Map - Default values for columns
- status: String - Session status (uploaded, mapped, processed, etc.)
- metadata: Map - Additional metadata

GLOBAL SECONDARY INDEXES:
- StatusIndex: status (Hash), created_at (Range)
- CreatedAtIndex: created_at (Hash)

-- ========================================
-- Templates Table
-- ========================================
TABLE: ExcelMapper_Templates
PRIMARY KEY: id (String)

ATTRIBUTES:
- id: String (Primary Key) - Unique template identifier
- name: String - Template name
- description: String - Template description
- created_at: String - ISO timestamp when created
- updated_at: String - ISO timestamp of last update
- created_by: String - User who created template
- usage_count: Number - Number of times template was used
- mappings: Map - Saved column mappings
- formula_rules: List - Template formula rules
- factwise_rules: List - Template Factwise ID rules
- default_values: Map - Template default values
- tags: List - Template tags for categorization
- is_public: Boolean - Whether template is public
- category: String - Template category

GLOBAL SECONDARY INDEXES:
- UsageCountIndex: usage_count (Hash), created_at (Range)
- CategoryIndex: category (Hash), created_at (Range)
- CreatedAtIndex: created_at (Hash)
- CreatedByIndex: created_by (Hash), created_at (Range)

-- ========================================
-- Tag Templates Table
-- ========================================
TABLE: ExcelMapper_TagTemplates
PRIMARY KEY: id (String)

ATTRIBUTES:
- id: String (Primary Key) - Unique tag template identifier
- name: String - Tag template name
- description: String - Tag template description
- created_at: String - ISO timestamp when created
- updated_at: String - ISO timestamp of last update
- created_by: String - User who created template
- usage_count: Number - Usage counter
- formula_rules: List - Tag generation rules
- tags: List - Categorization tags
- is_public: Boolean - Public availability

GLOBAL SECONDARY INDEXES:
- CreatedAtIndex: created_at (Hash)
- UsageCountIndex: usage_count (Hash), created_at (Range)

-- ========================================
-- Processing Jobs Table
-- ========================================
TABLE: ExcelMapper_ProcessingJobs
PRIMARY KEY: job_id (String)
TTL ATTRIBUTE: ttl

ATTRIBUTES:
- job_id: String (Primary Key) - Unique job identifier
- session_id: String - Associated session ID
- job_type: String - Type of processing job
- status: String - Job status (queued, processing, completed, failed)
- created_at: String - Job creation timestamp
- started_at: String - Job start timestamp
- completed_at: String - Job completion timestamp
- progress: Number - Job progress percentage (0-100)
- error_message: String - Error message if failed
- result: Map - Job result data
- ttl: Number - Unix timestamp for TTL (30 days)
- metadata: Map - Additional job metadata

GLOBAL SECONDARY INDEXES:
- StatusIndex: status (Hash), created_at (Range)
- SessionIndex: session_id (Hash), created_at (Range)
- JobTypeIndex: job_type (Hash), created_at (Range)

-- ========================================
-- Sample Data Structures
-- ========================================

-- Sessions Table Sample Item:
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:35:00Z",
  "ttl": 1705406100,
  "client_s3_key": "uploads/client_file_123.xlsx",
  "template_s3_key": "uploads/template_file_456.xlsx",
  "client_filename": "BOM_Parts_List.xlsx",
  "template_filename": "Standard_Template.xlsx",
  "sheet_name": "Sheet1",
  "header_row": 1,
  "template_sheet_name": "Template",
  "template_header_row": 1,
  "mappings": {
    "Item Code": "Part Number",
    "Item Name": "Description",
    "Quantity": "Qty"
  },
  "formula_rules": [
    {
      "source_column": "Description",
      "column_type": "Tag",
      "sub_rules": [
        {
          "search_text": "resistor",
          "output_value": "Resistor",
          "case_sensitive": false
        }
      ]
    }
  ],
  "status": "mapped"
}

-- Templates Table Sample Item:
{
  "id": "template_001",
  "name": "Electronics BOM Template",
  "description": "Standard template for electronics BOMs",
  "created_at": "2024-01-15T09:00:00Z",
  "updated_at": "2024-01-15T09:00:00Z",
  "created_by": "user123",
  "usage_count": 25,
  "mappings": {
    "Item Code": ["Part Number", "PN", "Part No"],
    "Item Name": ["Description", "Part Description"],
    "Quantity": ["Qty", "Count", "Amount"]
  },
  "formula_rules": [
    {
      "source_column": "Description",
      "column_type": "Tag",
      "sub_rules": [
        {
          "search_text": "capacitor",
          "output_value": "Capacitor"
        }
      ]
    }
  ],
  "tags": ["electronics", "bom", "standard"],
  "is_public": true,
  "category": "Electronics"
}

-- ========================================
-- DynamoDB Best Practices Implemented
-- ========================================

1. Single Table Design Principles:
   - Each table serves a specific domain
   - Proper partition key selection for even distribution
   - GSI for query patterns

2. Performance Optimizations:
   - Pay-per-request billing for variable workloads
   - Point-in-time recovery enabled
   - Stream processing for real-time updates

3. Data Lifecycle Management:
   - TTL configured for temporary data
   - Retention policies for log data
   - Automated cleanup processes

4. Security:
   - Encryption at rest enabled
   - IAM-based access control
   - No sensitive data in partition/sort keys

5. Cost Optimization:
   - Appropriate index selection
   - TTL for automatic cleanup
   - Pay-per-request for unpredictable traffic