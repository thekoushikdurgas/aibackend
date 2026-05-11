"""
Tests for Storage WebSocket Methods
"""

import base64

import pytest

from app.api.ws_methods.storage import (
    handle_storage_create_signed_url,
    handle_storage_delete,
    handle_storage_download,
    handle_storage_get_url,
    handle_storage_list,
    handle_storage_upload,
)
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode


@pytest.mark.asyncio
async def test_storage_upload_requires_auth():
    """Test that storage.upload requires authentication"""
    test_data = base64.b64encode(b"test content").decode()

    with pytest.raises(JSONRPCError) as exc_info:
        await handle_storage_upload(
            params={
                "bucket_type": "uploads",
                "file_path": "test.txt",
                "file_data": test_data,
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR


@pytest.mark.asyncio
async def test_storage_upload_invalid_params():
    """Test storage.upload with invalid parameters"""
    test_user = {"sub": "test_user_id", "type": "access"}

    with pytest.raises(JSONRPCError) as exc_info:
        await handle_storage_upload(
            params={
                "bucket_type": "uploads"
                # Missing file_path and file_data
            },
            user=test_user,
        )

    assert exc_info.value.code == JSONRPCErrorCode.INVALID_PARAMS


@pytest.mark.asyncio
async def test_storage_download_requires_auth():
    """Test that storage.download requires authentication"""
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_storage_download(
            params={
                "bucket_type": "uploads",
                "file_path": "test.txt",
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR


@pytest.mark.asyncio
async def test_storage_delete_requires_auth():
    """Test that storage.delete requires authentication"""
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_storage_delete(
            params={
                "bucket_type": "uploads",
                "file_path": "test.txt",
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR


@pytest.mark.asyncio
async def test_storage_list_requires_auth():
    """Test that storage.list requires authentication"""
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_storage_list(
            params={
                "bucket_type": "uploads",
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR


@pytest.mark.asyncio
async def test_storage_get_url_requires_auth():
    """Test that storage.get_url requires authentication"""
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_storage_get_url(
            params={
                "bucket_type": "uploads",
                "file_path": "test.txt",
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR


@pytest.mark.asyncio
async def test_storage_create_signed_url_requires_auth():
    """Test that storage.create_signed_url requires authentication"""
    with pytest.raises(JSONRPCError) as exc_info:
        await handle_storage_create_signed_url(
            params={
                "bucket_type": "uploads",
                "file_path": "test.txt",
            },
            user=None,
        )

    assert exc_info.value.code == JSONRPCErrorCode.AUTHENTICATION_ERROR
