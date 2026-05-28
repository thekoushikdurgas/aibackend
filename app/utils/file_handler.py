"""
File handling utilities for WebSocket (base64 encoding/decoding)
"""

import base64
import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


def decode_base64_file(file_data: Dict[str, Any]) -> Tuple[bytes, str]:
    """
    Decode base64 file data from WebSocket message

    Args:
        file_data: Dictionary with 'data' (base64 string) and 'mime_type'

    Returns:
        Tuple of (file_bytes, mime_type)
    """
    if not isinstance(file_data, dict):
        raise ValueError("file_data must be a dictionary")

    data = file_data.get("data")
    if not data:
        raise ValueError("Missing 'data' field in file_data")

    mime_type = file_data.get("mime_type", "application/octet-stream")

    try:
        # Handle data URL format (data:image/png;base64,...)
        if data.startswith("data:"):
            parts = data.split(",", 1)
            if len(parts) == 2:
                header = parts[0]
                data = parts[1]
                # Extract mime type from header
                if ";" in header:
                    mime_type = header.split(";")[0].replace("data:", "")

        # Decode base64
        file_bytes = base64.b64decode(data)
        return file_bytes, mime_type

    except Exception as e:
        raise ValueError(f"Failed to decode base64 file: {str(e)}")


def encode_base64_file(
    file_bytes: bytes, mime_type: str = "application/octet-stream"
) -> Dict[str, Any]:
    """
    Encode file bytes to base64 for WebSocket message

    Args:
        file_bytes: File bytes
        mime_type: MIME type of the file

    Returns:
        Dictionary with 'data' (base64 string) and 'mime_type'
    """
    try:
        data = base64.b64encode(file_bytes).decode("utf-8")
        return {"data": data, "mime_type": mime_type}
    except Exception as e:
        raise ValueError(f"Failed to encode file to base64: {str(e)}")


def handle_file_param(
    params: Dict[str, Any], param_name: str = "file"
) -> Optional[Tuple[bytes, str]]:
    """
    Extract and decode file from params

    Args:
        params: Parameters dictionary
        param_name: Name of the file parameter

    Returns:
        Tuple of (file_bytes, mime_type) or None if not present
    """
    file_data = params.get(param_name)
    if not file_data:
        return None

    if isinstance(file_data, str):
        # Assume it's a URL or base64 string
        if file_data.startswith("http://") or file_data.startswith("https://"):
            # URL - return as-is for services to handle
            return None
        elif file_data.startswith("data:") or len(file_data) > 100:
            # Likely base64 string
            file_data = {"data": file_data}

    if isinstance(file_data, dict):
        return decode_base64_file(file_data)

    return None
