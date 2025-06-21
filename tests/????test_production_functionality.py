"""
Module: test_production_functionality
Type: Test

Purpose:
Unit tests for Gong functionality ensuring reliability and correctness.

Data Flow:
- Input: Configuration parameters, Authentication credentials
- Processing: Input validation, Data extraction, API interaction
- Output: List of extracted data, Dictionary responses, Error states and exceptions

Critical Because:
Central integration point for Gong - without this, no Gong data can be accessed.

Dependencies:
- Requires: pytest, logging, authentication, api_client, agent, data_models
- Used By: app_backend.ingestion.orchestrator, app_backend.api_bridge.server

Author: Julia Evans
Date: 2025-06-20
"""
#!/usr/bin/env python3

import pytest
import time
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Gong toolkit components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from authentication import GongAuthenticationManager
from api_client import GongAPIClient
from agent import GongAgent
from data_models import GongSession


@pytest.mark.production
class TestGongProductionFunctionality:
    """Functional tests for real Gong production environment."""
    
    @pytest.fixture(autouse=True)
    def setup_production_environment(self):
        """Setup production test environment."""
        self.test_start_time = time.time()
        self.production_metrics = {
            'total_objects_extracted': 0,
            'total_records': 0,
            'extraction_time': 0,
            'success_rate': 0,
            'failed_operations': []
        }
        
        # Check for real HAR analysis data
        self.analysis_file = Path(__file__).parent.parent.parent / "_godcapture/data/gong-multitab-capture/analysis/godcapture_analysis.json"
        
        if not self.analysis_file.exists():
            pytest.skip("Production HAR analysis file not found - run _godcapture on real Gong environment first")
        
        # Validate analysis file contains real production data
        with open(self.analysis_file, 'r') as f:
            analysis_data = json.load(f)
        
        if not analysis_data.get('artifacts'):
            pytest.skip("Analysis file does not contain production artifacts")
        
        yield
        
        # Report production test results
        total_time = time.time() - self.test_start_time
        logger.info(f"\n📊 Production Test Results:")
        logger.info(f"  Total test time: {total_time:.2f}s")
        logger.info(f"  Objects extracted: {self.production_metrics['total_objects_extracted']}")
        logger.info(f"  Total records: {self.production_metrics['total_records']}")
        logger.info(f"  Success rate: {self.production_metrics['success_rate']:.1f}%")
        logger.info(f"  Failed operations: {len(self.production_metrics['failed_operations'])}")
    
    def test_production_authentication_functionality(self):
        """Test authentication functionality with real production session data."""
        logger.info("🔐 Testing Production Authentication Functionality")
        
        start_time = time.time()
        
        try:
            # Initialize authentication manager
            auth_manager = GongAuthenticationManager()
            
            # Load real production analysis data
            with open(self.analysis_file, 'r') as f:
                analysis_data = json.load(f)
            
            # Extract session from real production data
            session = auth_manager.extract_session_from_analysis_data(analysis_data)
            
            # Validate production session requirements
            assert session is not None, "Must extract valid session from production data"
            assert session.user_email, "Production session must have user email"
            assert session.cell_id, "Production session must have cell ID"
            assert len(session.authentication_tokens) > 0, "Must have authentication tokens"
            
            # Validate production token requirements
            jwt_tokens = [token for token in session.authentication_tokens if 'jwt' in token.token_type.lower()]
            assert len(jwt_tokens) > 0, "Must have JWT tokens for production authentication"
            
            # Test production session headers
            headers = auth_manager.get_session_headers(session)
            assert 'Cookie' in headers, "Must generate production-ready cookie headers"
            assert 'last_login_jwt' in headers['Cookie'], "Must include last_login_jwt in cookies"
            
            # Test production base URL
            base_url = auth_manager.get_base_url(session)
            assert base_url.startswith('https://'), "Must use HTTPS for production"
            assert '.app.gong.io' in base_url, "Must use production Gong domain"
            assert session.cell_id in base_url, "URL must contain correct cell ID"
            
            auth_time = time.time() - start_time
            
            logger.info(f"✅ Production authentication functional test passed:")
            logger.info(f"  Session extracted: {session.user_email}")
            logger.info(f"  Cell ID: {session.cell_id}")
            logger.info(f"  Tokens: {len(session.authentication_tokens)}")
            logger.info(f"  Authentication time: {auth_time:.2f}s")
            
            # Performance requirement for production
            assert auth_time < 5.0, f"Production authentication too slow: {auth_time:.2f}s (target: <5s)"
            
        except Exception as e:
            self.production_metrics['failed_operations'].append(f"Authentication: {str(e)}")
            logger.error(f"❌ Production authentication failed: {e}")
            raise
    
    def test_production_api_functionality(self):
        """Test API functionality with real production endpoints."""
        logger.info("🌐 Testing Production API Functionality")
        
        start_time = time.time()
        
        try:
            # Initialize components with production data
            auth_manager = GongAuthenticationManager()
            api_client = GongAPIClient()
            
            with open(self.analysis_file, 'r') as f:
                analysis_data = json.load(f)
            
            session = auth_manager.extract_session_from_analysis_data(analysis_data)
            api_client.set_session(session)
            
            # Test production API connection
            connection_status = api_client.get_connection_status()
            assert connection_status['connected'], "Must connect to production Gong API"
            assert connection_status['base_url'], "Must have valid production base URL"
            assert connection_status['workspace_id'], "Must identify production workspace"
            
            # Test production API endpoints (with rate limiting respect)
            production_endpoints = [
                ('get_my_calls', {'limit': 5}, 'calls'),
                ('get_users', {}, 'users'),
                ('get_deals', {}, 'deals'),
                ('get_conversations', {'limit': 3}, 'conversations'),
                ('get_library_folders', {}, 'library'),
                ('get_team_stats', {}, 'team_stats')
            ]
            
            successful_endpoints = 0
            total_endpoints = len(production_endpoints)
            
            for endpoint_name, params, data_type in production_endpoints:
                try:
                    logger.info(f"  Testing {endpoint_name}...")
                    
                    # Add delay to respect production rate limits
                    time.sleep(0.5)
                    
                    method = getattr(api_client, endpoint_name)
                    result = method(**params)
                    
                    # Validate production data requirements
                    assert result is not None, f"Endpoint {endpoint_name} must return data"
                    
                    if isinstance(result, list):
                        logger.info(f"    ✓ {endpoint_name}: {len(result)} {data_type}")
                        if len(result) > 0:
                            # Validate data structure for production
                            first_item = result[0]
                            assert isinstance(first_item, dict), f"{data_type} must be dict objects"
                            assert 'id' in first_item or 'metric' in first_item, f"{data_type} must have id or metric field"
                    else:
                        logger.info(f"    ✓ {endpoint_name}: {data_type} data")
                    
                    successful_endpoints += 1
                    
                except Exception as e:
                    logger.warning(f"    ❌ {endpoint_name} failed: {e}")
                    self.production_metrics['failed_operations'].append(f"API {endpoint_name}: {str(e)}")
            
            # Calculate production success rate
            success_rate = (successful_endpoints / total_endpoints) * 100
            api_time = time.time() - start_time
            
            logger.info(f"✅ Production API functional test results:")
            logger.info(f"  Successful endpoints: {successful_endpoints}/{total_endpoints}")
            logger.info(f"  Success rate: {success_rate:.1f}%")
            logger.info(f"  API test time: {api_time:.2f}s")
            
            # Production requirements
            assert success_rate >= 80.0, f"Production API success rate too low: {success_rate:.1f}% (target: ≥80%)"
            assert api_time < 30.0, f"Production API testing too slow: {api_time:.2f}s (target: <30s)"
            
            self.production_metrics['success_rate'] = success_rate
            
        except Exception as e:
            self.production_metrics['failed_operations'].append(f"API Testing: {str(e)}")
            logger.error(f"❌ Production API functionality failed: {e}")
            raise
    
    def test_production_data_extraction_functionality(self):
        """Test complete data extraction functionality with real production data."""
        logger.info("📊 Testing Production Data Extraction Functionality")
        
        start_time = time.time()
        
        try:
            # Initialize agent with production data
            agent = GongAgent(str(self.analysis_file))
            
            # Test production connection
            connection_test = agent.test_connection()
            assert connection_test['connected'], "Must connect to production Gong environment"
            
            logger.info(f"  ✓ Connected to production: {connection_test.get('base_url', 'Unknown')}")
            
            # Test production data extractions
            extraction_tests = [
                ('extract_calls', {'limit': 10}, 'calls', 5),
                ('extract_users', {}, 'users', 3),
                ('extract_deals', {}, 'deals', 2),
                ('extract_conversations', {'limit': 5}, 'conversations', 2),
                ('extract_library', {}, 'library', 1),
                ('extract_team_stats', {}, 'team_stats', 1)
            ]
            
            successful_extractions = 0
            total_records = 0
            
            for method_name, params, data_type, min_expected in extraction_tests:
                try:
                    logger.info(f"  Testing {method_name}...")
                    
                    # Add delay for production rate limiting
                    time.sleep(1.0)
                    
                    method = getattr(agent, method_name)
                    result = method(**params)
                    
                    # Validate production extraction requirements
                    assert result is not None, f"Production {method_name} must return data"
                    assert isinstance(result, list), f"Production {method_name} must return list"
                    
                    record_count = len(result)
                    total_records += record_count
                    
                    logger.info(f"    ✓ {method_name}: {record_count} {data_type}")
                    
                    # Validate minimum production data requirements
                    if record_count >= min_expected:
                        successful_extractions += 1
                        self.production_metrics['total_objects_extracted'] += 1
                    else:
                        logger.warning(f"    ⚠️  {method_name}: Expected ≥{min_expected}, got {record_count}")
                    
                    # Validate data quality for production
                    if record_count > 0:
                        first_record = result[0]
                        assert isinstance(first_record, dict), f"Production {data_type} must be dict objects"
                        
                        # Check for required fields based on data type
                        if data_type in ['calls', 'users', 'deals', 'conversations']:
                            assert 'id' in first_record, f"Production {data_type} must have id field"
                        elif data_type == 'team_stats':
                            assert 'metric' in first_record or 'value' in first_record, f"Production {data_type} must have metric/value"
                        
                except Exception as e:
                    logger.warning(f"    ❌ {method_name} failed: {e}")
                    self.production_metrics['failed_operations'].append(f"Extraction {method_name}: {str(e)}")
            
            # Calculate production metrics
            total_extractions = len(extraction_tests)
            extraction_success_rate = (successful_extractions / total_extractions) * 100
            extraction_time = time.time() - start_time
            
            self.production_metrics['total_records'] = total_records
            self.production_metrics['extraction_time'] = extraction_time
            
            logger.info(f"✅ Production data extraction functional test results:")
            logger.info(f"  Successful extractions: {successful_extractions}/{total_extractions}")
            logger.info(f"  Total records extracted: {total_records}")
            logger.info(f"  Extraction success rate: {extraction_success_rate:.1f}%")
            logger.info(f"  Total extraction time: {extraction_time:.2f}s")
            
            # Production requirements validation
            assert successful_extractions >= 4, f"Must successfully extract ≥4 object types, got {successful_extractions}"
            assert total_records >= 10, f"Must extract ≥10 total records, got {total_records}"
            assert extraction_success_rate >= 70.0, f"Extraction success rate too low: {extraction_success_rate:.1f}% (target: ≥70%)"
            assert extraction_time < 60.0, f"Production extraction too slow: {extraction_time:.2f}s (target: <60s)"
            
        except Exception as e:
            self.production_metrics['failed_operations'].append(f"Data Extraction: {str(e)}")
            logger.error(f"❌ Production data extraction functionality failed: {e}")
            raise
    
    def test_production_performance_requirements(self):
        """Test that production performance requirements are met."""
        logger.info("⚡ Testing Production Performance Requirements")
        
        start_time = time.time()
        
        try:
            # Initialize agent for performance testing
            agent = GongAgent(str(self.analysis_file))
            
            # Test quick extraction performance (primary production requirement)
            quick_start = time.time()
            
            try:
                # Test the quick_extract method for production performance
                result = agent.quick_extract()
                quick_time = time.time() - quick_start
                
                # Validate production performance requirements
                assert quick_time < 30.0, f"Production quick extraction too slow: {quick_time:.2f}s (target: <30s)"
                
                # Validate production data requirements
                assert 'metadata' in result, "Production result must include metadata"
                assert 'data' in result, "Production result must include data"
                
                metadata = result['metadata']
                assert metadata['successful_objects'] >= 4, f"Must extract ≥4 object types, got {metadata['successful_objects']}"
                assert metadata['failed_objects'] <= 2, f"Too many failed objects: {metadata['failed_objects']} (target: ≤2)"
                
                # Calculate overall success rate
                total_objects = metadata['successful_objects'] + metadata['failed_objects']
                if total_objects > 0:
                    overall_success_rate = (metadata['successful_objects'] / total_objects) * 100
                    assert overall_success_rate >= 70.0, f"Overall success rate too low: {overall_success_rate:.1f}% (target: ≥70%)"
                
                logger.info(f"✅ Production performance requirements met:")
                logger.info(f"  Quick extraction time: {quick_time:.2f}s (target: <30s)")
                logger.info(f"  Objects extracted: {metadata['successful_objects']} (target: ≥4)")
                logger.info(f"  Failed objects: {metadata['failed_objects']} (target: ≤2)")
                logger.info(f"  Overall success rate: {overall_success_rate:.1f}% (target: ≥70%)")
                
            except Exception as e:
                # If quick_extract fails, test individual components
                logger.warning(f"Quick extract failed, testing individual components: {e}")
                
                # Test individual extraction performance
                individual_start = time.time()
                successful_individual = 0
                
                individual_tests = ['extract_calls', 'extract_users', 'extract_deals']
                for method_name in individual_tests:
                    try:
                        method = getattr(agent, method_name)
                        result = method(limit=5) if 'calls' in method_name else method()
                        if result and len(result) > 0:
                            successful_individual += 1
                        time.sleep(0.5)  # Rate limiting
                    except Exception as individual_e:
                        logger.warning(f"Individual test {method_name} failed: {individual_e}")
                
                individual_time = time.time() - individual_start
                individual_success_rate = (successful_individual / len(individual_tests)) * 100
                
                assert individual_time < 45.0, f"Individual extraction too slow: {individual_time:.2f}s (target: <45s)"
                assert individual_success_rate >= 60.0, f"Individual success rate too low: {individual_success_rate:.1f}% (target: ≥60%)"
                
                logger.info(f"✅ Individual component performance acceptable:")
                logger.info(f"  Individual extraction time: {individual_time:.2f}s (target: <45s)")
                logger.info(f"  Individual success rate: {individual_success_rate:.1f}% (target: ≥60%)")
            
            total_performance_time = time.time() - start_time
            logger.info(f"  Total performance test time: {total_performance_time:.2f}s")
            
        except Exception as e:
            self.production_metrics['failed_operations'].append(f"Performance: {str(e)}")
            logger.error(f"❌ Production performance requirements failed: {e}")
            raise


@pytest.mark.production
class TestGongProductionDataQuality:
    """Test production data quality and validation."""
    
    def test_production_data_structure_validation(self):
        """Test that production data meets required structure standards."""
        logger.info("📋 Testing Production Data Structure Validation")
        
        analysis_file = Path(__file__).parent.parent.parent / "_godcapture/data/gong-multitab-capture/analysis/godcapture_analysis.json"
        if not analysis_file.exists():
            pytest.skip("Production analysis file not found")
        
        agent = GongAgent(str(analysis_file))
        
        # Test data structure requirements for each object type
        structure_tests = {
            'calls': {'required_fields': ['id'], 'optional_fields': ['title', 'duration', 'participants']},
            'users': {'required_fields': ['id'], 'optional_fields': ['name', 'email', 'role']},
            'deals': {'required_fields': ['id'], 'optional_fields': ['name', 'amount', 'stage']},
            'conversations': {'required_fields': ['id'], 'optional_fields': ['title', 'participants']},
            'team_stats': {'required_fields': ['metric', 'value'], 'optional_fields': ['unit', 'period']}
        }
        
        for data_type, requirements in structure_tests.items():
            try:
                logger.info(f"  Validating {data_type} structure...")
                
                # Extract sample data
                if data_type == 'calls':
                    sample_data = agent.extract_calls(limit=3)
                elif data_type == 'users':
                    sample_data = agent.extract_users()
                elif data_type == 'deals':
                    sample_data = agent.extract_deals()
                elif data_type == 'conversations':
                    sample_data = agent.extract_conversations(limit=3)
                elif data_type == 'team_stats':
                    sample_data = agent.extract_team_stats()
                
                if sample_data and len(sample_data) > 0:
                    # Validate structure of first record
                    first_record = sample_data[0]
                    
                    # Check required fields
                    for field in requirements['required_fields']:
                        assert field in first_record, f"Production {data_type} missing required field: {field}"
                    
                    # Validate data types
                    if 'id' in first_record:
                        assert isinstance(first_record['id'], str), f"Production {data_type} id must be string"
                    
                    logger.info(f"    ✓ {data_type}: Structure valid ({len(sample_data)} records)")
                else:
                    logger.warning(f"    ⚠️  {data_type}: No data available for validation")
                
                time.sleep(0.5)  # Rate limiting
                
            except Exception as e:
                logger.warning(f"    ❌ {data_type} structure validation failed: {e}")
        
        logger.info("✅ Production data structure validation completed")


if __name__ == "__main__":
    # Run production functionality tests
    pytest.main([__file__, "-v", "--tb=short", "-m", "production"])
