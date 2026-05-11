"""
Local filesystem storage WebSocket Methods.
"""

import base64
import logging
from typing import Any, Dict, Optional

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode
from app.core.ws_auth import require_auth
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)


async def handle_storage_upload(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    user = await require_auth(user, "storage.upload")

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
        try:
            file_data = base64.b64decode(file_data_base64)
        except Exception as e:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS, f"Invalid base64 data: {str(e)}"
            )

        user_id = user.get("sub") or user.get("id")
        if user_id:
            file_path = f"{user_id}/{file_path}"

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

        public_url = storage_service.get_public_url(bucket_type, result)
        signed_url = storage_service.create_signed_url(
            bucket_type, result, expires_in=3600
        )

        return {
            "success": True,
            "path": result,
            "public_url": public_url,
            "signed_url": signed_url,
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
    user = await require_auth(user, "storage.download")

    bucket_type = params.get("bucket_type", "uploads")
    file_path = params.get("file_path")

    if not file_path:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "file_path is required")

    try:
        storage_service = get_storage_service(use_admin=False)
        file_data = storage_service.download_file(bucket_type, file_path)

        if not file_data:
            raise JSONRPCError(
                JSONRPCErrorCode.INTERNAL_ERROR, "File not found or download failed"
            )

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
    user = await require_auth(user, "storage.delete")

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
    user = await require_auth(user, "storage.list")

    bucket_type = params.get("bucket_type", "uploads")
    folder_path = params.get("folder_path")
    limit = params.get("limit", 100)
    offset = params.get("offset", 0)

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
    user = await require_auth(user, "storage.move")

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
    user = await require_auth(user, "storage.get_url")

    bucket_type = params.get("bucket_type", "uploads")
    file_path = params.get("file_path")

    if not file_path:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "file_path is required")

    try:
        storage_service = get_storage_service(use_admin=False)
        signed_url = storage_service.create_signed_url(
            bucket_type, file_path, expires_in=3600
        )
        public_url = storage_service.get_public_url(bucket_type, file_path)

        return {
            "success": True,
            "url": signed_url or public_url,
            "public_url": public_url,
            "path": file_path,
        }

    except Exception as e:
        logger.error(f"Storage get_url error: {e}")
        raise JSONRPCError(JSONRPCErrorCode.INTERNAL_ERROR, f"Get URL failed: {str(e)}")


async def handle_storage_create_signed_url(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    user = await require_auth(user, "storage.create_signed_url")

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
            "signedURL": signed_url,
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
    user = await require_auth(user, "storage.buckets.list")

    try:
        storage_service = get_storage_service(use_admin=False)
        buckets = storage_service.list_buckets()
        return {"success": True, "buckets": buckets, "count": len(buckets)}

    except Exception as e:
        logger.error(f"Storage buckets list error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"List buckets failed: {str(e)}"
        )


async def handle_storage_buckets_create(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    user = await require_auth(user, "storage.buckets.create")

    bucket_name = params.get("name")
    is_public = params.get("public", False)

    if not bucket_name:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "name is required")

    try:
        storage_service = get_storage_service(use_admin=True)
        storage_service.create_bucket(bucket_name, is_public)

        return {"success": True, "bucket": {"name": bucket_name, "public": is_public}}

    except Exception as e:
        logger.error(f"Storage buckets create error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Create bucket failed: {str(e)}"
        )


async def handle_storage_buckets_delete(
    params: Dict[str, Any], user: Optional[Dict[str, Any]] = None, **kwargs
) -> Dict[str, Any]:
    user = await require_auth(user, "storage.buckets.delete")

    bucket_name = params.get("name")

    if not bucket_name:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "name is required")

    try:
        storage_service = get_storage_service(use_admin=True)
        storage_service.delete_bucket(bucket_name)

        return {"success": True, "bucket_name": bucket_name}

    except Exception as e:
        logger.error(f"Storage buckets delete error: {e}")
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Delete bucket failed: {str(e)}"
        )


def get_methods() -> Dict[str, Any]:
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
