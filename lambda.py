# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 AWS LAMBDA EXCEL MAPPER - ENTERPRISE SERVERLESS SOLUTION 
# ═══════════════════════════════════════════════════════════════════════════════

import json
import boto3
import uuid
import logging
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple, Union
import tempfile
import os
import io
import base64
from rapidfuzz import fuzz, distance
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill
import traceback
from decimal import Decimal

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 SHARED CONFIGURATION & UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

# AWS Configuration
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_BUCKET_UPLOADS = os.environ.get('S3_BUCKET_UPLOADS', 'excel-mapper-uploads')
S3_BUCKET_PROCESSED = os.environ.get('S3_BUCKET_PROCESSED', 'excel-mapper-processed')
S3_BUCKET_TEMPLATES = os.environ.get('S3_BUCKET_TEMPLATES', 'excel-mapper-templates')

# Initialize AWS clients with error handling
try:
    s3_client = boto3.client('s3', region_name=AWS_REGION)
    dynamodb = boto3.resource('dynamodb', region_name=AWS_REGION)
    
    # DynamoDB table references
    sessions_table = dynamodb.Table('ExcelMapper_Sessions')
    templates_table = dynamodb.Table('ExcelMapper_Templates')
    tag_templates_table = dynamodb.Table('ExcelMapper_TagTemplates')
    processing_jobs_table = dynamodb.Table('ExcelMapper_ProcessingJobs')
    
except Exception as e:
    logging.error(f"Failed to initialize AWS clients: {e}")
    raise

# Logging configuration
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Common response headers for CORS
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}

def lambda_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Standard Lambda response format with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, default=str)
    }

def handle_cors_preflight():
    """Handle CORS preflight requests"""
    return lambda_response(200, {'message': 'CORS preflight handled'})

def safe_decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: safe_decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [safe_decimal_to_float(v) for v in obj]
    return obj

# ═══════════════════════════════════════════════════════════════════════════════
# 🗂️ S3 FILE MANAGER - ROBUST FILE OPERATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class S3FileManager:
    """Enterprise-grade S3 file management for Excel operations"""
    
    def __init__(self):
        self.s3_client = s3_client
        self.upload_bucket = S3_BUCKET_UPLOADS
        self.processed_bucket = S3_BUCKET_PROCESSED
        self.templates_bucket = S3_BUCKET_TEMPLATES
    
    def save_upload_file(self, file_content: bytes, original_filename: str, prefix: str = "upload") -> Tuple[str, str]:
        """Save uploaded file to S3 and return S3 key and original filename"""
        try:
            file_extension = Path(original_filename).suffix
            unique_filename = f"{uuid.uuid4()}_{prefix}{file_extension}"
            s3_key = f"uploads/{unique_filename}"
            
            # Upload to S3 with metadata
            self.s3_client.put_object(
                Bucket=self.upload_bucket,
                Key=s3_key,
                Body=file_content,
                Metadata={
                    'original_filename': original_filename,
                    'upload_time': datetime.utcnow().isoformat(),
                    'file_type': file_extension
                }
            )
            
            logger.info(f"Successfully uploaded file {original_filename} to s3://{self.upload_bucket}/{s3_key}")
            return s3_key, original_filename
            
        except Exception as e:
            logger.error(f"Failed to upload file {original_filename}: {e}")
            raise
    
    def get_file_content(self, s3_key: str, bucket: str = None) -> bytes:
        """Retrieve file content from S3"""
        try:
            bucket = bucket or self.upload_bucket
            response = self.s3_client.get_object(Bucket=bucket, Key=s3_key)
            return response['Body'].read()
        except Exception as e:
            logger.error(f"Failed to retrieve file {s3_key}: {e}")
            raise
    
    def create_presigned_url(self, s3_key: str, expiration: int = 3600, bucket: str = None) -> str:
        """Generate presigned URL for secure file download"""
        try:
            bucket = bucket or self.processed_bucket
            url = self.s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            return url
        except Exception as e:
            logger.error(f"Failed to create presigned URL for {s3_key}: {e}")
            raise
    
    def save_processed_file(self, file_content: bytes, filename: str, session_id: str) -> str:
        """Save processed file to S3"""
        try:
            s3_key = f"processed/{session_id}/{filename}"
            self.s3_client.put_object(
                Bucket=self.processed_bucket,
                Key=s3_key,
                Body=file_content,
                Metadata={
                    'session_id': session_id,
                    'processed_time': datetime.utcnow().isoformat()
                }
            )
            return s3_key
        except Exception as e:
            logger.error(f"Failed to save processed file {filename}: {e}")
            raise
    
    def cleanup_old_files(self, days: int = 7):
        """Clean up old files from S3"""
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Clean upload bucket
            paginator = self.s3_client.get_paginator('list_objects_v2')
            for page in paginator.paginate(Bucket=self.upload_bucket):
                for obj in page.get('Contents', []):
                    if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                        self.s3_client.delete_object(Bucket=self.upload_bucket, Key=obj['Key'])
                        logger.info(f"Cleaned up old file: {obj['Key']}")
                        
        except Exception as e:
            logger.error(f"Failed to cleanup old files: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 📊 ADVANCED BOM HEADER MAPPER - AI-POWERED MAPPING
# ═══════════════════════════════════════════════════════════════════════════════

class AdvancedBOMHeaderMapper:
    """AI-powered header mapping with fuzzy matching and semantic understanding"""
    
    def __init__(self):
        self.min_confidence_threshold = 40
        self.similarity_weights = {
            'semantic': 0.40,
            'jaro_winkler': 0.25,
            'token_sort': 0.15,
            'partial_ratio': 0.10,
            'levenshtein': 0.10
        }
        
        # Comprehensive synonym mapping
        self.synonyms = {
            'item_code': ['part_number', 'part_no', 'item_id', 'sku', 'mpn', 'manufacturer_part_number'],
            'item_name': ['description', 'name', 'title', 'component', 'part_description'],
            'quantity': ['qty', 'amount', 'count', 'pieces', 'pcs'],
            'unit': ['uom', 'unit_of_measure', 'units'],
            'manufacturer': ['mfg', 'maker', 'brand', 'vendor', 'supplier'],
            'specification': ['spec', 'properties', 'specs', 'characteristics'],
            'value': ['val', 'data', 'rating', 'nominal'],
            'reference': ['ref', 'designator', 'ref_des', 'location'],
            'type': ['category', 'class', 'family', 'group'],
            'price': ['cost', 'rate', 'price_per_unit', 'unit_cost'],
            'voltage': ['v', 'volt', 'volts', 'vdc', 'vac'],
            'current': ['i', 'amp', 'amps', 'ampere', 'ma', 'ua'],
            'resistance': ['r', 'ohm', 'ohms', 'resistance'],
            'capacitance': ['c', 'cap', 'farad', 'uf', 'pf', 'nf'],
            'tolerance': ['tol', 'tolerance_percent', 'accuracy'],
            'package': ['footprint', 'case', 'housing', 'form_factor'],
            'temperature': ['temp', 'temp_range', 'operating_temp'],
            'power': ['p', 'power_rating', 'watts', 'w', 'power_dissipation']
        }
        
        self.abbreviations = {
            'qty': 'quantity',
            'desc': 'description',
            'mfg': 'manufacturer',
            'uom': 'unit',
            'ref': 'reference',
            'spec': 'specification',
            'val': 'value',
            'temp': 'temperature',
            'vol': 'voltage',
            'cur': 'current',
            'res': 'resistance',
            'cap': 'capacitance',
            'tol': 'tolerance'
        }
    
    def read_excel_headers(self, file_content: bytes, sheet_name: str = None, header_row: int = 0) -> List[str]:
        """Extract headers from Excel or CSV file content"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Read Excel file
                if sheet_name is None:
                    xl_file = pd.ExcelFile(tmp_file_path)
                    sheet_name = xl_file.sheet_names[0]
                
                df = pd.read_excel(tmp_file_path, sheet_name=sheet_name, header=header_row, nrows=1)
                headers = [str(col).strip() for col in df.columns if str(col).strip()]
                
                logger.info(f"Extracted {len(headers)} headers from {sheet_name}")
                return headers
                
            finally:
                # Clean up temp file
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Error reading Excel headers: {e}")
            return []
    
    def read_sample_data(self, file_content: bytes, sheet_name: str = None, header_row: int = 0, sample_rows: int = 5) -> Dict[str, List[str]]:
        """Read sample data for pattern analysis"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            try:
                if sheet_name is None:
                    xl_file = pd.ExcelFile(tmp_file_path)
                    sheet_name = xl_file.sheet_names[0]
                
                df = pd.read_excel(tmp_file_path, sheet_name=sheet_name, header=header_row, nrows=sample_rows)
                
                sample_data = {}
                for col in df.columns:
                    col_str = str(col).strip()
                    if col_str:
                        sample_data[col_str] = [str(val) for val in df[col].dropna().tolist()]
                
                return sample_data
                
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Error reading sample data: {e}")
            return {}
    
    def calculate_semantic_similarity(self, header1: str, header2: str) -> float:
        """Calculate semantic similarity using synonym matching"""
        if not header1 or not header2:
            return 0.0
        
        header1_lower = header1.lower().strip()
        header2_lower = header2.lower().strip()
        
        # Direct match
        if header1_lower == header2_lower:
            return 1.0
        
        # Check synonyms
        for canonical, synonyms in self.synonyms.items():
            if header1_lower in synonyms and header2_lower in synonyms:
                return 0.95
            if header1_lower == canonical and header2_lower in synonyms:
                return 0.9
            if header2_lower == canonical and header1_lower in synonyms:
                return 0.9
        
        # Check abbreviations
        expanded1 = self.abbreviations.get(header1_lower, header1_lower)
        expanded2 = self.abbreviations.get(header2_lower, header2_lower)
        
        if expanded1 == expanded2:
            return 0.85
        
        return 0.0
    
    def map_headers_to_template(self, client_content: bytes, template_content: bytes, 
                               client_sheet: str = None, template_sheet: str = None,
                               client_header_row: int = 0, template_header_row: int = 0) -> List[Dict]:
        """Advanced header mapping with AI suggestions"""
        try:
            template_headers = self.read_excel_headers(template_content, template_sheet, template_header_row)
            client_headers = self.read_excel_headers(client_content, client_sheet, client_header_row)
            
            client_sample_data = self.read_sample_data(client_content, client_sheet, client_header_row)
            
            results = []
            used_client_headers = set()
            
            for template_header in template_headers:
                best_match = None
                best_score = 0.0
                best_explanation = ""
                
                for client_header in client_headers:
                    if client_header in used_client_headers:
                        continue
                    
                    # Calculate comprehensive similarity score
                    semantic_score = self.calculate_semantic_similarity(template_header, client_header)
                    jaro_score = fuzz.ratio(template_header.lower(), client_header.lower()) / 100.0
                    token_score = fuzz.token_sort_ratio(template_header.lower(), client_header.lower()) / 100.0
                    partial_score = fuzz.partial_ratio(template_header.lower(), client_header.lower()) / 100.0
                    
                    # Weighted average
                    final_score = (
                        semantic_score * self.similarity_weights['semantic'] +
                        jaro_score * self.similarity_weights['jaro_winkler'] +
                        token_score * self.similarity_weights['token_sort'] +
                        partial_score * self.similarity_weights['partial_ratio']
                    )
                    
                    if final_score > best_score:
                        best_score = final_score
                        best_match = client_header
                        
                        if semantic_score > 0:
                            best_explanation = f"Semantic match (score: {semantic_score:.2f})"
                        else:
                            best_explanation = f"Fuzzy match (score: {final_score:.2f})"
                
                confidence = int(best_score * 100)
                
                if best_match and confidence >= self.min_confidence_threshold:
                    used_client_headers.add(best_match)
                    mapped_header = best_match
                else:
                    mapped_header = None
                
                sample_data = client_sample_data.get(mapped_header, []) if mapped_header else []
                
                results.append({
                    'template_header': template_header,
                    'mapped_client_header': mapped_header,
                    'confidence': confidence,
                    'explanation': best_explanation,
                    'sample_data': sample_data[:3]
                })
            
            logger.info(f"Mapped {len([r for r in results if r['mapped_client_header']])} out of {len(template_headers)} headers")
            return results
            
        except Exception as e:
            logger.error(f"Error in header mapping: {e}")
            return []

# ═══════════════════════════════════════════════════════════════════════════════
# 🔄 DATA TRANSFORMATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class DataTransformationEngine:
    """Advanced data transformation with formula rules and Factwise ID generation"""
    
    def __init__(self):
        self.file_manager = S3FileManager()
    
    def apply_column_mappings(self, client_content: bytes, mappings: Dict, 
                             sheet_name: str = None, header_row: int = 0) -> Dict[str, Any]:
        """Apply column mappings with support for duplicate mappings"""
        try:
            logger.info(f"Applying mappings: {mappings}")
            
            # Read client data
            with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
                tmp_file.write(client_content)
                tmp_file_path = tmp_file.name
            
            try:
                if str(tmp_file_path).lower().endswith('.csv'):
                    df = pd.read_csv(tmp_file_path, header=header_row)
                else:
                    result = pd.read_excel(tmp_file_path, sheet_name=sheet_name, header=header_row)
                    
                    if isinstance(result, dict):
                        first_sheet_name = list(result.keys())[0]
                        df = result[first_sheet_name]
                    else:
                        df = result
                
                # Clean column names
                df.columns = [str(col).strip() for col in df.columns]
                
                # Process mappings
                mapping_list = []
                if isinstance(mappings, dict) and 'mappings' in mappings:
                    mapping_list = mappings['mappings']
                elif isinstance(mappings, list):
                    mapping_list = mappings
                else:
                    for target, source in mappings.items():
                        if isinstance(source, list):
                            for src in source:
                                mapping_list.append({'source': src, 'target': target})
                        else:
                            mapping_list.append({'source': source, 'target': target})
                
                # Build column order
                mapped_targets = []
                mapping_dict = {}
                
                for mapping in mapping_list:
                    target = mapping['target']
                    if target not in mapping_dict:
                        mapping_dict[target] = []
                        mapped_targets.append(target)
                    mapping_dict[target].append(mapping)
                
                column_order = mapped_targets.copy()
                
                # Process each row
                transformed_rows = []
                for _, row in df.iterrows():
                    transformed_row = []
                    
                    for target_column in column_order:
                        if target_column in mapping_dict:
                            mappings_for_target = mapping_dict[target_column]
                            for mapping in mappings_for_target:
                                source_column = mapping['source']
                                
                                if source_column and source_column in df.columns:
                                    value = row.get(source_column, "")
                                    if pd.isna(value):
                                        value = ""
                                    else:
                                        value = str(value).strip()
                                    transformed_row.append(value)
                                else:
                                    transformed_row.append("")
                        else:
                            transformed_row.append("")
                    
                    transformed_rows.append(transformed_row)
                
                # Build headers with unique names
                final_headers = []
                counts = {}
                
                for target_column in column_order:
                    if target_column in mapping_dict:
                        for _ in mapping_dict[target_column]:
                            if target_column not in counts:
                                counts[target_column] = 1
                                final_headers.append(target_column)
                            else:
                                counts[target_column] += 1
                                new_header = f"{target_column}_{counts[target_column]}"
                                while new_header in final_headers:
                                    counts[target_column] += 1
                                    new_header = f"{target_column}_{counts[target_column]}"
                                final_headers.append(new_header)
                    else:
                        final_headers.append(target_column)
                
                return {
                    'headers': final_headers,
                    'data': transformed_rows
                }
                
            finally:
                os.unlink(tmp_file_path)
                
        except Exception as e:
            logger.error(f"Error in apply_column_mappings: {e}")
            return {'headers': [], 'data': []}
    
    def apply_formula_rules(self, data_rows: List[Dict], headers: List[str], 
                           formula_rules: List[Dict]) -> Dict[str, Any]:
        """Apply formula rules with sub-rules support"""
        if not data_rows or not formula_rules:
            return {'data': data_rows, 'headers': headers, 'new_columns': []}
        
        modified_data = [row.copy() for row in data_rows]
        new_headers = headers.copy()
        new_columns = []
        
        used_column_names = set(headers)
        tag_counter = 1
        spec_counter = 1
        
        for rule_index, rule in enumerate(formula_rules):
            source_column = rule.get('source_column')
            column_type = rule.get('column_type', 'Tag')
            specification_name = rule.get('specification_name', '')
            sub_rules = rule.get('sub_rules', [])
            
            if not source_column or not sub_rules:
                continue
            
            if column_type == 'Tag':
                column_name = f"Tag_{tag_counter}"
                while column_name in used_column_names:
                    tag_counter += 1
                    column_name = f"Tag_{tag_counter}"
                
                new_headers.append(column_name)
                new_columns.append(column_name)
                used_column_names.add(column_name)
                tag_counter += 1
                
                for row in modified_data:
                    if column_name not in row:
                        row[column_name] = ''
                    
                    for sub_rule in sub_rules:
                        search_text = sub_rule.get('search_text', '')
                        output_value = sub_rule.get('output_value', '')
                        case_sensitive = sub_rule.get('case_sensitive', False)
                        
                        if not search_text or not output_value:
                            continue
                        
                        cell_value = str(row.get(source_column, ''))
                        search_text_compare = search_text if case_sensitive else search_text.lower()
                        cell_value_compare = cell_value if case_sensitive else cell_value.lower()
                        
                        if search_text_compare in cell_value_compare:
                            existing_value = row.get(column_name, '').strip()
                            
                            if existing_value and existing_value != output_value:
                                existing_values = [v.strip() for v in existing_value.split(',')]
                                if output_value not in existing_values:
                                    row[column_name] = f"{existing_value}, {output_value}"
                            else:
                                row[column_name] = output_value
                            break
            
            elif column_type == 'Specification Value' and specification_name:
                name_column = f"Specification_Name_{spec_counter}"
                value_column = f"Specification_Value_{spec_counter}"
                
                while name_column in used_column_names or value_column in used_column_names:
                    spec_counter += 1
                    name_column = f"Specification_Name_{spec_counter}"
                    value_column = f"Specification_Value_{spec_counter}"
                
                new_headers.extend([name_column, value_column])
                new_columns.extend([name_column, value_column])
                used_column_names.update([name_column, value_column])
                
                for row in modified_data:
                    if name_column not in row:
                        row[name_column] = specification_name
                    if value_column not in row:
                        row[value_column] = ''
                    
                    for sub_rule in sub_rules:
                        search_text = sub_rule.get('search_text', '')
                        output_value = sub_rule.get('output_value', '')
                        case_sensitive = sub_rule.get('case_sensitive', False)
                        
                        if not search_text or not output_value:
                            continue
                        
                        cell_value = str(row.get(source_column, ''))
                        search_text_compare = search_text if case_sensitive else search_text.lower()
                        cell_value_compare = cell_value if case_sensitive else cell_value.lower()
                        
                        if search_text_compare in cell_value_compare:
                            existing_value = row.get(value_column, '').strip()
                            
                            if existing_value and existing_value != output_value:
                                existing_values = [v.strip() for v in existing_value.split(',')]
                                if output_value not in existing_values:
                                    row[value_column] = f"{existing_value}, {output_value}"
                            else:
                                row[value_column] = output_value
                            break
                
                spec_counter += 1
        
        return {
            'data': modified_data,
            'headers': new_headers,
            'new_columns': new_columns,
            'total_rows': len(modified_data)
        }
    
    def create_factwise_id(self, data_rows: List[Dict], headers: List[str], 
                          first_column: str, second_column: str, operator: str = '_') -> Dict[str, Any]:
        """Create Factwise ID column"""
        if not data_rows or first_column not in headers or second_column not in headers:
            return {'data': data_rows, 'headers': headers}
        
        new_headers = ["Factwise_ID"] + headers
        new_data_rows = []
        
        for row in data_rows:
            first_val = str(row.get(first_column, '')).strip()
            second_val = str(row.get(second_column, '')).strip()
            
            if first_val and second_val:
                factwise_id = f"{first_val}{operator}{second_val}"
            elif first_val:
                factwise_id = first_val
            elif second_val:
                factwise_id = second_val
            else:
                factwise_id = ""
            
            new_row = {"Factwise_ID": factwise_id, **row}
            new_data_rows.append(new_row)
        
        return {
            'data': new_data_rows,
            'headers': new_headers
        }

# ═══════════════════════════════════════════════════════════════════════════════
# 🗄️ SESSION MANAGEMENT WITH DYNAMODB
# ═══════════════════════════════════════════════════════════════════════════════

class SessionManager:
    """DynamoDB-based session management"""
    
    def __init__(self):
        self.sessions_table = sessions_table
        self.ttl_hours = 24
    
    def create_session(self, session_data: Dict[str, Any]) -> str:
        """Create new session in DynamoDB"""
        try:
            session_id = str(uuid.uuid4())
            ttl = int((datetime.utcnow() + timedelta(hours=self.ttl_hours)).timestamp())
            
            item = {
                'session_id': session_id,
                'created_at': datetime.utcnow().isoformat(),
                'ttl': ttl,
                **session_data
            }
            
            self.sessions_table.put_item(Item=item)
            logger.info(f"Created session {session_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from DynamoDB"""
        try:
            response = self.sessions_table.get_item(Key={'session_id': session_id})
            
            if 'Item' in response:
                return response['Item']
            return None
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]):
        """Update session data in DynamoDB"""
        try:
            update_expression = "SET "
            expression_values = {}
            
            for key, value in updates.items():
                update_expression += f"{key} = :{key}, "
                expression_values[f":{key}"] = value
            
            update_expression = update_expression.rstrip(", ")
            
            self.sessions_table.update_item(
                Key={'session_id': session_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values
            )
            
            logger.info(f"Updated session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            raise
    
    def delete_session(self, session_id: str):
        """Delete session from DynamoDB"""
        try:
            self.sessions_table.delete_item(Key={'session_id': session_id})
            logger.info(f"Deleted session {session_id}")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")

# ═══════════════════════════════════════════════════════════════════════════════
# 🔧 TEMPLATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

class TemplateManager:
    """DynamoDB-based template management"""
    
    def __init__(self):
        self.templates_table = templates_table
        self.tag_templates_table = tag_templates_table
    
    def save_mapping_template(self, template_data: Dict[str, Any]) -> str:
        """Save mapping template to DynamoDB"""
        try:
            template_id = str(uuid.uuid4())
            
            item = {
                'id': template_id,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat(),
                'usage_count': 0,
                **template_data
            }
            
            self.templates_table.put_item(Item=item)
            logger.info(f"Saved mapping template {template_id}")
            return template_id
            
        except Exception as e:
            logger.error(f"Failed to save mapping template: {e}")
            raise
    
    def get_mapping_templates(self) -> List[Dict[str, Any]]:
        """Get all mapping templates"""
        try:
            response = self.templates_table.scan()
            templates = response.get('Items', [])
            
            # Convert Decimal to float for JSON serialization
            templates = safe_decimal_to_float(templates)
            
            return templates
            
        except Exception as e:
            logger.error(f"Failed to get mapping templates: {e}")
            return []
    
    def apply_template(self, template_id: str, client_headers: List[str]) -> Dict[str, Any]:
        """Apply template mappings to client headers"""
        try:
            response = self.templates_table.get_item(Key={'id': template_id})
            
            if 'Item' not in response:
                raise ValueError(f"Template {template_id} not found")
            
            template = response['Item']
            mappings = template.get('mappings', {})
            
            applied_mappings = {}
            total_mapped = 0
            
            # Apply fuzzy matching for template application
            for template_col, original_source in mappings.items():
                matched_source = None
                
                # Try exact match first
                if original_source in client_headers:
                    matched_source = original_source
                else:
                    # Try fuzzy matching
                    best_match = None
                    best_score = 0
                    
                    for client_header in client_headers:
                        score = fuzz.ratio(original_source.lower(), client_header.lower())
                        if score > best_score and score > 70:
                            best_score = score
                            best_match = client_header
                    
                    if best_match:
                        matched_source = best_match
                
                if matched_source:
                    applied_mappings[template_col] = matched_source
                    total_mapped += 1
            
            # Increment usage count
            self.templates_table.update_item(
                Key={'id': template_id},
                UpdateExpression="SET usage_count = usage_count + :inc",
                ExpressionAttributeValues={':inc': 1}
            )
            
            return {
                'mappings': applied_mappings,
                'total_mapped': total_mapped,
                'total_template_columns': len(mappings),
                'formula_rules': template.get('formula_rules', []),
                'factwise_rules': template.get('factwise_rules', []),
                'default_values': template.get('default_values', {})
            }
            
        except Exception as e:
            logger.error(f"Failed to apply template {template_id}: {e}")
            raise

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 LAMBDA FUNCTION HANDLERS
# ═══════════════════════════════════════════════════════════════════════════════

# ──────────────────────────────────────────────────────────────────────────────
# 📤 UPLOAD HANDLER LAMBDA
# ──────────────────────────────────────────────────────────────────────────────

def upload_handler(event, context):
    """Handle file uploads with template application"""
    try:
        # Handle CORS preflight
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        # Parse multipart form data from base64 encoded body
        body = event.get('body', '')
        if event.get('isBase64Encoded'):
            body = base64.b64decode(body)
        
        # Extract files and form data (simplified for demo)
        # In production, use a proper multipart parser
        form_data = json.loads(body) if isinstance(body, str) else {}
        
        client_file_data = form_data.get('clientFile')
        template_file_data = form_data.get('templateFile')
        
        if not client_file_data or not template_file_data:
            return lambda_response(400, {
                'success': False,
                'error': 'Both client and template files are required'
            })
        
        # Decode base64 file content
        client_content = base64.b64decode(client_file_data['content'])
        template_content = base64.b64decode(template_file_data['content'])
        
        # Save files to S3
        file_manager = S3FileManager()
        client_key, client_name = file_manager.save_upload_file(
            client_content, client_file_data['filename'], "client"
        )
        template_key, template_name = file_manager.save_upload_file(
            template_content, template_file_data['filename'], "template"
        )
        
        # Create session
        session_manager = SessionManager()
        session_data = {
            'client_s3_key': client_key,
            'template_s3_key': template_key,
            'client_filename': client_name,
            'template_filename': template_name,
            'sheet_name': form_data.get('sheetName'),
            'header_row': int(form_data.get('headerRow', 1)),
            'template_sheet_name': form_data.get('templateSheetName'),
            'template_header_row': int(form_data.get('templateHeaderRow', 1)),
            'formula_rules': json.loads(form_data.get('formulaRules', '[]')),
            'status': 'uploaded'
        }
        
        session_id = session_manager.create_session(session_data)
        
        # Apply template if specified
        template_applied = False
        applied_mappings = {}
        use_template_id = form_data.get('useTemplateId')
        
        if use_template_id:
            try:
                template_manager = TemplateManager()
                mapper = AdvancedBOMHeaderMapper()
                
                # Read client headers
                client_headers = mapper.read_excel_headers(
                    client_content,
                    session_data['sheet_name'],
                    session_data['header_row'] - 1
                )
                
                # Apply template
                result = template_manager.apply_template(use_template_id, client_headers)
                
                if result['total_mapped'] > 0:
                    template_applied = True
                    applied_mappings = result['mappings']
                    
                    # Update session with applied mappings
                    session_manager.update_session(session_id, {
                        'mappings': result,
                        'template_id': use_template_id,
                        'template_applied': True
                    })
                
            except Exception as e:
                logger.error(f"Template application failed: {e}")
        
        return lambda_response(201, {
            'success': True,
            'session_id': session_id,
            'message': 'Files uploaded successfully',
            'template_applied': template_applied,
            'applied_mappings': applied_mappings
        })
        
    except Exception as e:
        logger.error(f"Upload handler error: {e}")
        logger.error(traceback.format_exc())
        return lambda_response(500, {
            'success': False,
            'error': f'Upload failed: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 📊 HEADERS HANDLER LAMBDA
# ──────────────────────────────────────────────────────────────────────────────

def headers_handler(event, context):
    """Get headers from uploaded files"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        session_id = event['pathParameters']['session_id']
        
        session_manager = SessionManager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return lambda_response(404, {
                'success': False,
                'error': 'Session not found'
            })
        
        file_manager = S3FileManager()
        mapper = AdvancedBOMHeaderMapper()
        
        # Get file contents from S3
        client_content = file_manager.get_file_content(session['client_s3_key'])
        template_content = file_manager.get_file_content(session['template_s3_key'])
        
        # Read headers
        client_headers = mapper.read_excel_headers(
            client_content,
            session.get('sheet_name'),
            session.get('header_row', 1) - 1
        )
        
        template_headers = mapper.read_excel_headers(
            template_content,
            session.get('template_sheet_name'),
            session.get('template_header_row', 1) - 1
        )
        
        return lambda_response(200, {
            'success': True,
            'client_headers': client_headers,
            'template_headers': template_headers
        })
        
    except Exception as e:
        logger.error(f"Headers handler error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to get headers: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 🎯 MAPPING SUGGESTIONS HANDLER LAMBDA
# ──────────────────────────────────────────────────────────────────────────────

def mapping_suggestions_handler(event, context):
    """Generate AI-powered mapping suggestions"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        
        if not session_id:
            return lambda_response(400, {
                'success': False,
                'error': 'Session ID is required'
            })
        
        session_manager = SessionManager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return lambda_response(404, {
                'success': False,
                'error': 'Session not found'
            })
        
        file_manager = S3FileManager()
        mapper = AdvancedBOMHeaderMapper()
        
        # Get file contents
        client_content = file_manager.get_file_content(session['client_s3_key'])
        template_content = file_manager.get_file_content(session['template_s3_key'])
        
        # Get mapping suggestions
        mapping_results = mapper.map_headers_to_template(
            client_content,
            template_content,
            session.get('sheet_name'),
            session.get('template_sheet_name'),
            session.get('header_row', 1) - 1,
            session.get('template_header_row', 1) - 1
        )
        
        # Prepare AI suggestions
        ai_suggestions = {}
        for result in mapping_results:
            if result['mapped_client_header'] and result['confidence'] >= 40:
                ai_suggestions[result['template_header']] = {
                    'suggested_column': result['mapped_client_header'],
                    'confidence': result['confidence'],
                    'is_specification_mapping': False
                }
        
        # Get headers for response
        client_headers = mapper.read_excel_headers(
            client_content,
            session.get('sheet_name'),
            session.get('header_row', 1) - 1
        )
        
        template_headers = mapper.read_excel_headers(
            template_content,
            session.get('template_sheet_name'),
            session.get('template_header_row', 1) - 1
        )
        
        return lambda_response(200, {
            'success': True,
            'ai_suggestions': ai_suggestions,
            'mapping_details': mapping_results,
            'template_headers': template_headers,
            'client_headers': client_headers,
            'user_columns': client_headers,
            'template_columns': template_headers,
            'specification_opportunity': {'detected': False}
        })
        
    except Exception as e:
        logger.error(f"Mapping suggestions error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to generate suggestions: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 💾 SAVE MAPPINGS HANDLER LAMBDA
# ──────────────────────────────────────────────────────────────────────────────

def save_mappings_handler(event, context):
    """Save column mappings for a session"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        mappings = body.get('mappings', {})
        default_values = body.get('default_values', {})
        
        if not session_id:
            return lambda_response(400, {
                'success': False,
                'error': 'Session ID is required'
            })
        
        session_manager = SessionManager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return lambda_response(404, {
                'success': False,
                'error': 'Session not found'
            })
        
        # Update session with mappings
        session_manager.update_session(session_id, {
            'mappings': mappings,
            'default_values': default_values,
            'status': 'mapped'
        })
        
        return lambda_response(200, {
            'success': True,
            'message': 'Mappings saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Save mappings error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to save mappings: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 📈 DATA VIEW HANDLER LAMBDA
# ──────────────────────────────────────────────────────────────────────────────

def data_view_handler(event, context):
    """Get transformed data with applied mappings"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        query_params = event.get('queryStringParameters', {}) or {}
        session_id = query_params.get('session_id')
        page = int(query_params.get('page', 1))
        page_size = int(query_params.get('page_size', 20))
        
        if not session_id:
            return lambda_response(400, {
                'success': False,
                'error': 'Session ID is required'
            })
        
        session_manager = SessionManager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return lambda_response(400, {
                'success': False,
                'error': 'Session not found'
            })
        
        mappings = session.get('mappings')
        if not mappings:
            return lambda_response(400, {
                'success': False,
                'error': 'No mappings found'
            })
        
        # Get transformed data
        file_manager = S3FileManager()
        transformer = DataTransformationEngine()
        
        client_content = file_manager.get_file_content(session['client_s3_key'])
        
        # Apply mappings
        mapping_result = transformer.apply_column_mappings(
            client_content,
            mappings,
            session.get('sheet_name'),
            session.get('header_row', 1) - 1
        )
        
        transformed_rows = mapping_result['data']
        headers = mapping_result['headers']
        
        # Apply formula rules if they exist
        formula_rules = session.get('formula_rules', [])
        if formula_rules and transformed_rows:
            # Convert to dict format for formula processing
            dict_rows = []
            for row_list in transformed_rows:
                row_dict = {}
                for i, header in enumerate(headers):
                    if i < len(row_list):
                        row_dict[header] = row_list[i]
                    else:
                        row_dict[header] = ""
                dict_rows.append(row_dict)
            
            formula_result = transformer.apply_formula_rules(
                dict_rows, headers, formula_rules
            )
            
            transformed_rows = formula_result['data']
            headers = formula_result['headers']
        
        # Apply default values
        default_values = session.get('default_values', {})
        if default_values and transformed_rows:
            for row in transformed_rows:
                for field_name, default_value in default_values.items():
                    if field_name in headers:
                        current_value = row.get(field_name, "")
                        if not current_value or current_value == "":
                            row[field_name] = default_value
        
        # Implement pagination
        total_rows = len(transformed_rows)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_rows = transformed_rows[start_idx:end_idx]
        
        return lambda_response(200, {
            'success': True,
            'data': paginated_rows,
            'headers': headers,
            'formula_rules': formula_rules,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_rows': total_rows,
                'total_pages': (total_rows + page_size - 1) // page_size
            }
        })
        
    except Exception as e:
        logger.error(f"Data view error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to get data: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 📥 DOWNLOAD HANDLER LAMBDA
# ──────────────────────────────────────────────────────────────────────────────

def download_handler(event, context):
    """Generate download URLs for processed files"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        file_format = body.get('format', 'excel')
        
        if not session_id:
            return lambda_response(400, {
                'success': False,
                'error': 'Session ID is required'
            })
        
        session_manager = SessionManager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return lambda_response(404, {
                'success': False,
                'error': 'Session not found'
            })
        
        # Get transformed data
        file_manager = S3FileManager()
        transformer = DataTransformationEngine()
        
        client_content = file_manager.get_file_content(session['client_s3_key'])
        mappings = session.get('mappings', {})
        
        if not mappings:
            return lambda_response(400, {
                'success': False,
                'error': 'No mappings found'
            })
        
        # Apply transformations
        mapping_result = transformer.apply_column_mappings(
            client_content,
            mappings,
            session.get('sheet_name'),
            session.get('header_row', 1) - 1
        )
        
        # Create Excel or CSV file
        df = pd.DataFrame(mapping_result['data'], columns=mapping_result['headers'])
        
        # Generate file content
        if file_format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            file_content = output.getvalue().encode('utf-8')
            filename = f"processed_data_{session_id}.csv"
            content_type = 'text/csv'
        else:
            output = io.BytesIO()
            df.to_excel(output, index=False, engine='openpyxl')
            file_content = output.getvalue()
            filename = f"processed_data_{session_id}.xlsx"
            content_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        
        # Save to S3 and generate presigned URL
        s3_key = file_manager.save_processed_file(file_content, filename, session_id)
        download_url = file_manager.create_presigned_url(s3_key, expiration=3600)
        
        return lambda_response(200, {
            'success': True,
            'download_url': download_url,
            'filename': filename,
            'expires_in': 3600
        })
        
    except Exception as e:
        logger.error(f"Download handler error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Download failed: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 🏷️ TEMPLATE MANAGEMENT HANDLERS
# ──────────────────────────────────────────────────────────────────────────────

def template_save_handler(event, context):
    """Save mapping template"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        body = json.loads(event.get('body', '{}'))
        
        template_manager = TemplateManager()
        template_id = template_manager.save_mapping_template(body)
        
        return lambda_response(201, {
            'success': True,
            'template_id': template_id,
            'message': 'Template saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Template save error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to save template: {str(e)}'
        })

def template_list_handler(event, context):
    """Get all mapping templates"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        template_manager = TemplateManager()
        templates = template_manager.get_mapping_templates()
        
        return lambda_response(200, {
            'success': True,
            'templates': templates
        })
        
    except Exception as e:
        logger.error(f"Template list error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to get templates: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 🔧 FORMULA HANDLERS
# ──────────────────────────────────────────────────────────────────────────────

def apply_formulas_handler(event, context):
    """Apply formula rules to session data"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        formula_rules = body.get('formula_rules', [])
        
        if not session_id:
            return lambda_response(400, {
                'success': False,
                'error': 'Session ID is required'
            })
        
        session_manager = SessionManager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return lambda_response(404, {
                'success': False,
                'error': 'Session not found'
            })
        
        # Update session with formula rules
        session_manager.update_session(session_id, {
            'formula_rules': formula_rules
        })
        
        return lambda_response(200, {
            'success': True,
            'message': f'Applied {len(formula_rules)} formula rules successfully',
            'rules_applied': len(formula_rules)
        })
        
    except Exception as e:
        logger.error(f"Apply formulas error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to apply formulas: {str(e)}'
        })

def create_factwise_id_handler(event, context):
    """Create Factwise ID column"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        body = json.loads(event.get('body', '{}'))
        session_id = body.get('session_id')
        first_column = body.get('first_column')
        second_column = body.get('second_column')
        operator = body.get('operator', '_')
        
        if not all([session_id, first_column, second_column]):
            return lambda_response(400, {
                'success': False,
                'error': 'Session ID, first_column, and second_column are required'
            })
        
        session_manager = SessionManager()
        session = session_manager.get_session(session_id)
        
        if not session:
            return lambda_response(404, {
                'success': False,
                'error': 'Session not found'
            })
        
        # Store Factwise ID rule
        factwise_rule = {
            'type': 'factwise_id',
            'first_column': first_column,
            'second_column': second_column,
            'operator': operator
        }
        
        factwise_rules = session.get('factwise_rules', [])
        factwise_rules = [r for r in factwise_rules if r.get('type') != 'factwise_id']
        factwise_rules.append(factwise_rule)
        
        session_manager.update_session(session_id, {
            'factwise_rules': factwise_rules
        })
        
        return lambda_response(200, {
            'success': True,
            'message': 'Factwise ID rule saved successfully'
        })
        
    except Exception as e:
        logger.error(f"Create Factwise ID error: {e}")
        return lambda_response(500, {
            'success': False,
            'error': f'Failed to create Factwise ID: {str(e)}'
        })

# ──────────────────────────────────────────────────────────────────────────────
# 🏥 HEALTH CHECK HANDLER
# ──────────────────────────────────────────────────────────────────────────────

def health_check_handler(event, context):
    """Health check endpoint"""
    try:
        if event.get('httpMethod') == 'OPTIONS':
            return handle_cors_preflight()
        
        return lambda_response(200, {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '2.0.0',
            'service': 'Excel Mapper Lambda'
        })
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return lambda_response(500, {
            'status': 'unhealthy',
            'error': str(e)
        })

# ═══════════════════════════════════════════════════════════════════════════════
# 🎯 MAIN ROUTER FUNCTION (OPTIONAL - FOR SINGLE LAMBDA ARCHITECTURE)
# ═══════════════════════════════════════════════════════════════════════════════

def main_router(event, context):
    """Main router for all Excel Mapper operations"""
    try:
        path = event.get('path', '')
        method = event.get('httpMethod', 'GET')
        
        # Route to appropriate handler
        if path == '/health' and method == 'GET':
            return health_check_handler(event, context)
        elif path == '/upload' and method == 'POST':
            return upload_handler(event, context)
        elif path.startswith('/headers/') and method == 'GET':
            return headers_handler(event, context)
        elif path == '/mapping' and method == 'POST':
            return mapping_suggestions_handler(event, context)
        elif path == '/mapping/save' and method == 'POST':
            return save_mappings_handler(event, context)
        elif path == '/data' and method == 'GET':
            return data_view_handler(event, context)
        elif path == '/download' and method == 'POST':
            return download_handler(event, context)
        elif path == '/templates/save' and method == 'POST':
            return template_save_handler(event, context)
        elif path == '/templates' and method == 'GET':
            return template_list_handler(event, context)
        elif path == '/formulas/apply' and method == 'POST':
            return apply_formulas_handler(event, context)
        elif path == '/create-factwise-id' and method == 'POST':
            return create_factwise_id_handler(event, context)
        else:
            return lambda_response(404, {
                'success': False,
                'error': f'Endpoint not found: {method} {path}'
            })
            
    except Exception as e:
        logger.error(f"Router error: {e}")
        logger.error(traceback.format_exc())
        return lambda_response(500, {
            'success': False,
            'error': 'Internal server error'
        })

# ═══════════════════════════════════════════════════════════════════════════════
# 🚀 EXPORT HANDLERS FOR INDIVIDUAL LAMBDA FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

# Individual handlers for separate Lambda functions
lambda_upload = upload_handler
lambda_headers = headers_handler
lambda_mapping_suggestions = mapping_suggestions_handler
lambda_save_mappings = save_mappings_handler
lambda_data_view = data_view_handler
lambda_download = download_handler
lambda_template_save = template_save_handler
lambda_template_list = template_list_handler
lambda_apply_formulas = apply_formulas_handler
lambda_create_factwise_id = create_factwise_id_handler
lambda_health_check = health_check_handler

# Main router for single Lambda architecture
lambda_main_router = main_router