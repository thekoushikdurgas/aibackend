# Supabase Storage via WebSocket

This document describes the Supabase Storage WebSocket methods available in the DurgasAI backend.

## Overview

All storage operations are handled through WebSocket using JSON-RPC 2.0 protocol. Files are uploaded as base64-encoded data and automatically scoped by user ID for security.

## Configuration

Storage buckets are configured in `config/config.json`:

```json
{
  "supabase": {
    "storage_buckets": {
      "uploads": "user-uploads",
      "avatars": "user-avatars",
      "documents": "rag-documents"
    }
  }
}
```

## Available Methods

### storage.upload

Upload file to Supabase Storage. **Requires authentication.**

**Parameters:**

- `bucket_type` (string, required): Type of bucket ("uploads", "avatars", "documents")
- `file_path` (string, required): Path within bucket
- `file_data` (string, required): Base64-encoded file content
- `content_type` (string, optional): MIME type (e.g., "image/png")
- `metadata` (object, optional): File metadata

**Response:**

```json
{
  "success": true,
  "path": "user-id/filename.ext",
  "public_url": "https://...",
  "bucket_type": "uploads"
}
```

**Example:**

```javascript
const fileData = btoa(fileContent); // Base64 encode
ws.send(
  JSON.stringify({
    jsonrpc: '2.0',
    id: 'req-1',
    method: 'storage.upload',
    params: {
      bucket_type: 'uploads',
      file_path: 'document.pdf',
      file_data: fileData,
      content_type: 'application/pdf',
    },
    auth: { type: 'jwt', token: '...' },
  })
);
```

### storage.download

Download file from Supabase Storage. **Requires authentication.**

**Parameters:**

- `bucket_type` (string, required): Type of bucket
- `file_path` (string, required): Path within bucket

**Response:**

```json
{
  "success": true,
  "file_data": "base64-encoded-content",
  "path": "user-id/filename.ext",
  "size": 12345
}
```

### storage.delete

Delete file from Supabase Storage. **Requires authentication.**

**Parameters:**

- `bucket_type` (string, required): Type of bucket
- `file_path` (string, required): Path within bucket

**Response:**

```json
{
  "success": true,
  "path": "user-id/filename.ext"
}
```

### storage.list

List files in a bucket folder. **Requires authentication.**

**Parameters:**

- `bucket_type` (string, required): Type of bucket
- `folder_path` (string, optional): Folder path (defaults to user's folder)
- `limit` (integer, optional): Maximum number of files (default 100)
- `offset` (integer, optional): Offset for pagination (default 0)

**Response:**

```json
{
  "success": true,
  "files": [
    {
      "name": "filename.ext",
      "id": "file-id",
      "updated_at": "2024-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z",
      "last_accessed_at": "2024-01-01T00:00:00Z",
      "metadata": {}
    }
  ],
  "count": 10,
  "bucket_type": "uploads",
  "folder_path": "user-id"
}
```

### storage.move

Move/rename file in storage. **Requires authentication.**

**Parameters:**

- `bucket_type` (string, required): Type of bucket
- `from_path` (string, required): Current file path
- `to_path` (string, required): New file path

**Response:**

```json
{
  "success": true,
  "from_path": "old-path",
  "to_path": "new-path"
}
```

### storage.get_url

Get public URL for a file. **Requires authentication.**

**Parameters:**

- `bucket_type` (string, required): Type of bucket
- `file_path` (string, required): Path within bucket

**Response:**

```json
{
  "success": true,
  "url": "https://...",
  "path": "user-id/filename.ext"
}
```

### storage.create_signed_url

Create signed URL for private file access. **Requires authentication.**

**Parameters:**

- `bucket_type` (string, required): Type of bucket
- `file_path` (string, required): Path within bucket
- `expires_in` (integer, optional): Expiration time in seconds (default 3600)

**Response:**

```json
{
  "success": true,
  "signed_url": "https://...?token=...",
  "path": "user-id/filename.ext",
  "expires_in": 3600
}
```

### storage.buckets.list

List available storage buckets. **Requires authentication.**

**Parameters:** None

**Response:**

```json
{
  "success": true,
  "buckets": [
    {
      "id": "bucket-id",
      "name": "user-uploads",
      "public": false,
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "count": 3
}
```

### storage.buckets.create

Create new bucket (admin only). **Requires authentication and admin privileges.**

**Parameters:**

- `name` (string, required): Bucket name
- `public` (boolean, optional): Make bucket public (default false)

**Response:**

```json
{
  "success": true,
  "bucket": {
    "name": "new-bucket",
    "public": false
  }
}
```

### storage.buckets.delete

Delete bucket (admin only). **Requires authentication and admin privileges.**

**Parameters:**

- `name` (string, required): Bucket name

**Response:**

```json
{
  "success": true,
  "bucket_name": "bucket-to-delete"
}
```

## File Path Scoping

All file uploads are automatically scoped by user ID for security:

- User uploads: `{user_id}/filename.ext`
- Avatars: `{user_id}/avatar/filename.ext`
- Documents: `{user_id}/documents/filename.ext`

This ensures users can only access their own files.

## Frontend Integration

The frontend uses `storage_client` which wraps all WebSocket calls:

```python
from services.storage_client import storage_client

# Upload file
with open("file.pdf", "rb") as f:
    file_data = f.read()
    response = storage_client.upload_file_sync(
        bucket_type="uploads",
        file_path="document.pdf",
        file_data=file_data,
        content_type="application/pdf"
    )

# Download file
file_data = storage_client.download_file_sync(
    bucket_type="uploads",
    file_path="user-id/document.pdf"
)

# List files
response = storage_client.list_files_sync(
    bucket_type="uploads",
    folder_path="user-id"
)

# Get public URL
url = storage_client.get_public_url_sync(
    bucket_type="uploads",
    file_path="user-id/document.pdf"
)

# Create signed URL
signed_url = storage_client.create_signed_url_sync(
    bucket_type="uploads",
    file_path="user-id/document.pdf",
    expires_in=3600
)
```

See [frontend/services/storage_client.py](../frontend/services/storage_client.py) for complete API.

## Best Practices

1. **File Size**: Consider chunking large files (>10MB) for better performance
2. **Content Types**: Always specify `content_type` for proper MIME type handling
3. **Error Handling**: Check `success` field in responses before using data
4. **Signed URLs**: Use signed URLs for private files instead of public URLs
5. **Cleanup**: Delete temporary files after processing
6. **Metadata**: Use metadata to store file information (size, original name, etc.)

## Security Considerations

- All storage methods require authentication
- Files are automatically scoped by user ID
- Admin operations (bucket create/delete) require service role key
- Public buckets should be used carefully
- Signed URLs expire after specified time

## Error Handling

All methods return JSON-RPC error responses on failure:

```json
{
  "jsonrpc": "2.0",
  "id": "req-1",
  "error": {
    "code": -32001,
    "message": "Authentication required",
    "data": null
  }
}
```

Common error codes:

- `-32602`: Invalid parameters (e.g., missing file_path)
- `-32001`: Authentication error
- `-32603`: Internal error (e.g., upload failed)
