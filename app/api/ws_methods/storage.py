"""
Supabase Storage WebSocket Methods
"""

import base64
import logging
from typing import Dict, Any, Optional

from app.core.supabase_client import (
    get_supabase_client,
    get_supabase_admin_client,
    is_supabase_configured,
)
from app.core.ws_auth import require_auth
from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)


async def handle_storage_upload(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.upload - Upload file (base64 encoded)

    Args:
        params: {
            "bucket_type": str (uploads, avatars, documents),
            "file_path": str,
            "file_data": str (base64 encoded),
            "content_type": str (optional),
            "metadata": dict (optional)
        }
    """
    user = await require_auth(user, "storage.upload")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_type = params.get("bucket_type", "uploads")
    file_path = params.get("file_path")
    file_data_base64 = params.get("file_data")
    content_type = params.get("content_type")
    metadata = params.get("metadata")

    if not file_path or not file_data_base64:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "file_path and file_data are required"
        )

    try:
        # Decode base64
        try:
            file_data = base64.b64decode(file_data_base64)
        except Exception as e:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS, f"Invalid base64 data: {str(e)}"
            )

        # Scope file path by user ID
        user_id = user.get("sub") or user.get("id")
        if user_id:
            file_path = f"{user_id}/{file_path}"

        # Upload to Supabase Storage
        storage_service = get_storage_service(use_admin=False)
        result = storage_service.upload_file(
            bucket_type=bucket_type,
            file_path=file_path,
            file_data=file_data,
            content_type=content_type,
            metadata=metadata,
        )

        if not result:
            raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, "Failed to upload file")

        # Get public URL if available
        public_url = storage_service.get_public_url(bucket_type, result)

        return {
            "success": True,
            "path": result,
            "public_url": public_url,
            "bucket_type": bucket_type,
        }

    except JSONRPCError:
        raise
    except Exception as e:
        logger.error(f"Storage upload error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Upload failed: {str(e)}")


async def handle_storage_download(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.download - Download file (returns base64)

    Args:
        params: {
            "bucket_type": str,
            "file_path": str
        }
    """
    user = await require_auth(user, "storage.download")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_type = params.get("bucket_type", "uploads")
    file_path = params.get("file_path")

    if not file_path:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "file_path is required")

    try:
        # Download from Supabase Storage
        storage_service = get_storage_service(use_admin=False)
        file_data = storage_service.download_file(bucket_type, file_path)

        if not file_data:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "File not found or download failed"
            )

        # Encode to base64
        file_data_base64 = base64.b64encode(file_data).decode("utf-8")

        return {
            "success": True,
            "file_data": file_data_base64,
            "path": file_path,
            "size": len(file_data),
        }

    except JSONRPCError:
        raise
    except Exception as e:
        logger.error(f"Storage download error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Download failed: {str(e)}"
        )


async def handle_storage_delete(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.delete - Delete file

    Args:
        params: {
            "bucket_type": str,
            "file_path": str
        }
    """
    user = await require_auth(user, "storage.delete")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_type = params.get("bucket_type", "uploads")
    file_path = params.get("file_path")

    if not file_path:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "file_path is required")

    try:
        storage_service = get_storage_service(use_admin=False)
        success = storage_service.delete_file(bucket_type, file_path)

        return {"success": success, "path": file_path}

    except Exception as e:
        logger.error(f"Storage delete error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Delete failed: {str(e)}")


async def handle_storage_list(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.list - List files in folder

    Args:
        params: {
            "bucket_type": str,
            "folder_path": str (optional),
            "limit": int (optional, default 100),
            "offset": int (optional, default 0)
        }
    """
    user = await require_auth(user, "storage.list")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_type = params.get("bucket_type", "uploads")
    folder_path = params.get("folder_path")
    limit = params.get("limit", 100)
    offset = params.get("offset", 0)

    # Scope to user's folder if no specific folder provided
    if not folder_path:
        user_id = user.get("sub") or user.get("id")
        if user_id:
            folder_path = user_id

    try:
        storage_service = get_storage_service(use_admin=False)
        files = storage_service.list_files(
            bucket_type=bucket_type, folder_path=folder_path, limit=limit, offset=offset
        )

        return {
            "success": True,
            "files": files,
            "count": len(files),
            "bucket_type": bucket_type,
            "folder_path": folder_path,
        }

    except Exception as e:
        logger.error(f"Storage list error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"List failed: {str(e)}")


async def handle_storage_move(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.move - Move/rename file

    Args:
        params: {
            "bucket_type": str,
            "from_path": str,
            "to_path": str
        }
    """
    user = await require_auth(user, "storage.move")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_type = params.get("bucket_type", "uploads")
    from_path = params.get("from_path")
    to_path = params.get("to_path")

    if not from_path or not to_path:
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "from_path and to_path are required"
        )

    try:
        storage_service = get_storage_service(use_admin=False)
        success = storage_service.move_file(bucket_type, from_path, to_path)

        return {"success": success, "from_path": from_path, "to_path": to_path}

    except Exception as e:
        logger.error(f"Storage move error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Move failed: {str(e)}")


async def handle_storage_get_url(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.get_url - Get public URL

    Args:
        params: {
            "bucket_type": str,
            "file_path": str
        }
    """
    user = await require_auth(user, "storage.get_url")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_type = params.get("bucket_type", "uploads")
    file_path = params.get("file_path")

    if not file_path:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "file_path is required")

    try:
        storage_service = get_storage_service(use_admin=False)
        public_url = storage_service.get_public_url(bucket_type, file_path)

        return {"success": True, "url": public_url, "path": file_path}

    except Exception as e:
        logger.error(f"Storage get_url error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Get URL failed: {str(e)}")


async def handle_storage_create_signed_url(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.create_signed_url - Create signed URL for private files

    Args:
        params: {
            "bucket_type": str,
            "file_path": str,
            "expires_in": int (optional, default 3600 seconds)
        }
    """
    user = await require_auth(user, "storage.create_signed_url")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_type = params.get("bucket_type", "uploads")
    file_path = params.get("file_path")
    expires_in = params.get("expires_in", 3600)

    if not file_path:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "file_path is required")

    try:
        storage_service = get_storage_service(use_admin=False)
        signed_url = storage_service.create_signed_url(
            bucket_type=bucket_type, file_path=file_path, expires_in=expires_in
        )

        if not signed_url:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to create signed URL"
            )

        return {
            "success": True,
            "signed_url": signed_url,
            "path": file_path,
            "expires_in": expires_in,
        }

    except JSONRPCError:
        raise
    except Exception as e:
        logger.error(f"Storage create_signed_url error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Create signed URL failed: {str(e)}"
        )


async def handle_storage_buckets_list(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.buckets.list - List available buckets

    Args:
        params: {} (optional)
    """
    user = await require_auth(user, "storage.buckets.list")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    try:
        supabase = get_supabase_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "Failed to initialize Supabase client"
            )

        # List buckets
        response = supabase.storage.list_buckets()

        buckets = []
        if response:
            for bucket in response:
                buckets.append(
                    {
                        "id": bucket.id,
                        "name": bucket.name,
                        "public": bucket.public if hasattr(bucket, "public") else False,
                        "created_at": (
                            bucket.created_at if hasattr(bucket, "created_at") else None
                        ),
                        "updated_at": (
                            bucket.updated_at if hasattr(bucket, "updated_at") else None
                        ),
                    }
                )

        return {"success": True, "buckets": buckets, "count": len(buckets)}

    except Exception as e:
        logger.error(f"Storage buckets list error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"List buckets failed: {str(e)}"
        )


async def handle_storage_buckets_create(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.buckets.create - Create new bucket (admin only)

    Args:
        params: {
            "name": str,
            "public": bool (optional, default False)
        }
    """
    user = await require_auth(user, "storage.buckets.create")

    # Check if user is admin (you can enhance this with role checking)
    # For now, we'll use admin client which requires service role key
    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_name = params.get("name")
    is_public = params.get("public", False)

    if not bucket_name:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "name is required")

    try:
        # Use admin client for bucket creation
        supabase = get_supabase_admin_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR,
                "Admin access required. Service role key not configured.",
            )

        # Create bucket
        supabase.storage.create_bucket(bucket_name, options={"public": is_public})

        return {"success": True, "bucket": {"name": bucket_name, "public": is_public}}

    except Exception as e:
        logger.error(f"Storage buckets create error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Create bucket failed: {str(e)}"
        )


async def handle_storage_buckets_delete(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    """
    Handle storage.buckets.delete - Delete bucket (admin only)

    Args:
        params: {
            "name": str
        }
    """
    user = await require_auth(user, "storage.buckets.delete")

    if not is_supabase_configured():
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, "Supabase is not configured"
        )

    bucket_name = params.get("name")

    if not bucket_name:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "name is required")

    try:
        # Use admin client for bucket deletion
        supabase = get_supabase_admin_client()
        if not supabase:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR,
                "Admin access required. Service role key not configured.",
            )

        # Delete bucket
        supabase.storage.delete_bucket(bucket_name)

        return {"success": True, "bucket_name": bucket_name}

    except Exception as e:
        logger.error(f"Storage buckets delete error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Delete bucket failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
    """Return all storage methods from this module"""
    return {
        "storage.upload": handle_storage_upload,
        "storage.download": handle_storage_download,
        "storage.delete": handle_storage_delete,
        "storage.list": handle_storage_list,
        "storage.move": handle_storage_move,
        "storage.get_url": handle_storage_get_url,
        "storage.create_signed_url": handle_storage_create_signed_url,
        "storage.buckets.list": handle_storage_buckets_list,
        "storage.buckets.create": handle_storage_buckets_create,
        "storage.buckets.delete": handle_storage_buckets_delete,
    }
