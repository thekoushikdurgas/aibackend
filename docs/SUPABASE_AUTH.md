# Supabase Authentication via WebSocket

This document describes the Supabase authentication WebSocket methods available in the DurgasAI backend.

## Overview

All authentication operations are handled through WebSocket using JSON-RPC 2.0 protocol. The backend communicates directly with Supabase, and the frontend never directly accesses Supabase.

## Configuration

Add Supabase configuration to `config/config.json`:

```json
{
  "supabase": {
    "url": "https://your-project.supabase.co",
    "anon_key": "your-anon-key",
    "service_role_key": "your-service-role-key",
    "jwt_secret": "your-jwt-secret"
  }
}
```

## Available Methods

### auth.signup

Register a new user with email and password.

**Parameters:**

- `email` (string, required): User email address
- `password` (string, required): User password
- `metadata` (object, optional): User metadata

**Response:**

```json
{
  "success": true,
  "user": {
    "id": "user-id",
    "email": "user@example.com",
    "user_metadata": {},
    "app_metadata": {}
  },
  "session": {
    "access_token": "jwt-token",
    "refresh_token": "refresh-token",
    "expires_in": 3600,
    "expires_at": 1234567890
  },
  "requires_confirmation": false
}
```

**Example:**

```javascript
ws.send(
  JSON.stringify({
    jsonrpc: '2.0',
    id: 'req-1',
    method: 'auth.signup',
    params: {
      email: 'user@example.com',
      password: 'secure_password',
      metadata: { username: 'johndoe' },
    },
  })
);
```

### auth.signin

Sign in with email and password.

**Parameters:**

- `email` (string, required): User email address
- `password` (string, required): User password

**Response:**

```json
{
  "success": true,
  "user": {...},
  "session": {...}
}
```

### auth.signout

Sign out and invalidate current session.

**Parameters:** None

**Response:**

```json
{
  "success": true,
  "message": "Signed out successfully"
}
```

### auth.refresh

Refresh JWT token using refresh token.

**Parameters:**

- `refresh_token` (string, optional): Refresh token (uses current session if not provided)

**Response:**

```json
{
  "success": true,
  "session": {
    "access_token": "new-jwt-token",
    "refresh_token": "new-refresh-token",
    ...
  }
}
```

### auth.verify

Verify JWT token validity.

**Parameters:**

- `token` (string, optional): Token to verify (uses current session if not provided)

**Response:**

```json
{
  "valid": true,
  "user": {...}
}
```

### auth.reset_password_request

Request password reset email.

**Parameters:**

- `email` (string, required): User email address
- `redirect_to` (string, optional): Redirect URL after password reset

**Response:**

```json
{
  "success": true,
  "message": "Password reset email sent"
}
```

### auth.reset_password

Complete password reset with token.

**Parameters:**

- `token` (string, required): Reset token from email
- `new_password` (string, required): New password

**Response:**

```json
{
  "success": true,
  "message": "Password reset successfully",
  "user": {...}
}
```

### auth.update_user

Update user metadata/profile. **Requires authentication.**

**Parameters:**

- `metadata` (object, optional): User metadata to update
- `email` (string, optional): New email address
- `password` (string, optional): New password

**Response:**

```json
{
  "success": true,
  "user": {...}
}
```

### auth.magic_link

Send magic link email for passwordless authentication.

**Parameters:**

- `email` (string, required): User email address
- `redirect_to` (string, optional): Redirect URL after magic link click

**Response:**

```json
{
  "success": true,
  "message": "Magic link email sent"
}
```

### auth.oauth_url

Get OAuth provider authorization URL.

**Parameters:**

- `provider` (string, required): OAuth provider (e.g., "google", "github")
- `redirect_to` (string, optional): Redirect URL after OAuth

**Response:**

```json
{
  "success": true,
  "url": "https://oauth-provider.com/authorize?...",
  "provider": "google"
}
```

### auth.oauth_callback

Handle OAuth callback (typically handled via URL redirect).

**Parameters:**

- `code` (string, required): OAuth code from callback
- `provider` (string, optional): OAuth provider

**Response:**

```json
{
  "success": true,
  "message": "OAuth callback processed"
}
```

## Authentication Flow

1. **Sign Up**: User registers with email/password
2. **Email Confirmation**: User confirms email (if required)
3. **Sign In**: User signs in with credentials
4. **Session Management**: Access token stored in frontend, refresh token used to renew session
5. **Token Refresh**: Automatically refresh token before expiration
6. **Sign Out**: Invalidate session and clear tokens

## Security Considerations

- All storage and auth methods validate user authentication
- JWT tokens are validated using Supabase JWT secret
- Service role key is only used for admin operations (never exposed to frontend)
- Row Level Security (RLS) is respected when using anon key
- File uploads are automatically scoped by user ID

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

- `-32602`: Invalid parameters
- `-32001`: Authentication error
- `-32603`: Internal error

## Frontend Integration

The frontend uses `auth_service` which wraps all WebSocket calls:

```python
from services.auth_service import auth_service

# Sign up
response = auth_service.signup_sync("user@example.com", "password")

# Sign in
response = auth_service.signin_sync("user@example.com", "password")

# Sign out
auth_service.signout_sync()

# Refresh session
response = auth_service.refresh_session_sync()
```

See [frontend/services/auth_service.py](../frontend/services/auth_service.py) for complete API.
