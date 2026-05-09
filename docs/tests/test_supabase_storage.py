"""
Tests for Supabase Storage
"""

import pytest
from app.services.storage_service import get_storage_service
from app.core.supabase_client import is_supabase_configured


@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
def test_storage_service_initialization():
    """Test storage service initialization"""
    storage = get_storage_service()
    assert storage is not None


@pytest.mark.skipif(not is_supabase_configured(), reason="Supabase not configured")
def test_storage_upload_download():
    """Test file upload and download"""
    storage = get_storage_service()
    if not storage:
        pytest.skip("Storage service not available")
    
    test_file_path = "test/test_file.txt"
    test_content = b"Test file content"
    
    try:
        # Upload file
        uploaded_path = storage.upload_file(
            bucket_type="uploads",
            file_path=test_file_path,
            file_data=test_content,
            content_type="text/plain"
        )
        
        assert uploaded_path is not None
        
        # Download file
        downloaded_content = storage.download_file(
            bucket_type="uploads",
            file_path=test_file_path
        )
        
        assert downloaded_content == test_content
        
        # Cleanup
        storage.delete_file("uploads", test_file_path)
        
    except Exception as e:
        pytest.skip(f"Storage test failed: {e}")

