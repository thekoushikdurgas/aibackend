"""
Tests for WebSocket File Upload (Base64)
"""

import pytest
import base64
from app.utils.file_handler import (
    decode_base64_file, encode_base64_file, handle_file_param
)


def test_encode_decode_file():
    """Test encoding and decoding files"""
    test_data = b"Hello, World! This is test binary data."
    mime_type = "text/plain"
    
    # Encode
    encoded = encode_base64_file(test_data, mime_type)
    assert "data" in encoded
    assert encoded["mime_type"] == mime_type
    
    # Decode
    decoded_data, decoded_mime = decode_base64_file(encoded)
    assert decoded_data == test_data
    assert decoded_mime == mime_type


def test_decode_data_url():
    """Test decoding data URL format"""
    test_data = b"test image data"
    base64_data = base64.b64encode(test_data).decode("utf-8")
    data_url = f"data:image/png;base64,{base64_data}"
    
    file_data = {"data": data_url}
    decoded_data, mime_type = decode_base64_file(file_data)
    
    assert decoded_data == test_data
    assert mime_type == "image/png"


def test_handle_file_param_dict():
    """Test handle_file_param with dictionary"""
    test_data = b"test file content"
    encoded = encode_base64_file(test_data, "text/plain")
    
    params = {"file": encoded}
    result = handle_file_param(params, "file")
    
    assert result is not None
    decoded_data, mime_type = result
    assert decoded_data == test_data
    assert mime_type == "text/plain"


def test_handle_file_param_string():
    """Test handle_file_param with string (URL)"""
    params = {"file": "https://example.com/image.png"}
    result = handle_file_param(params, "file")
    
    # Should return None for URLs (services handle them)
    assert result is None


def test_handle_file_param_missing():
    """Test handle_file_param with missing file"""
    params = {}
    result = handle_file_param(params, "file")
    assert result is None


def test_decode_invalid_base64():
    """Test decoding invalid base64"""
    file_data = {"data": "invalid base64!!!"}
    
    with pytest.raises(ValueError):
        decode_base64_file(file_data)

