# Supabase Integration Setup Guide

This guide will help you set up Supabase for authentication, storage, and real-time features in DurgasAI.

## Prerequisites

1. A Supabase account (sign up at https://supabase.com)
2. A Supabase project created
3. Your Supabase project URL and anon key

## Step 1: Create Supabase Project

1. Go to https://supabase.com and sign in
2. Create a new project
3. Note your project URL and anon key from Settings > API

## Step 2: Configure Environment Variables

Add to your `.env` file or `config.json`:

```json
{
  "supabase": {
    "url": "https://your-project.supabase.co",
    "anon_key": "your-anon-key",
    "service_role_key": "your-service-role-key",
    "storage_buckets": {
      "uploads": "user-uploads",
      "avatars": "user-avatars",
      "documents": "rag-documents"
    }
  }
}
```

## Step 3: Run Database Schema

1. Open your Supabase project dashboard
2. Go to SQL Editor
3. Run the schema file: `backend/scripts/supabase_schema.sql`
4. Run the storage setup: `backend/scripts/setup_storage_buckets.sql`

## Step 4: Configure Authentication Providers (Optional)

To enable OAuth providers (Google, GitHub, etc.):

1. Go to Authentication > Providers in Supabase dashboard
2. Enable desired providers
3. Configure OAuth credentials for each provider
4. Add redirect URLs:
   - Development: `http://localhost:8501`
   - Production: Your production URL

## Step 5: Install Dependencies

```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd frontend
pip install -r requirements.txt
```

## Step 6: Verify Setup

1. Start the backend:

   ```bash
   cd backend
   python -m app.main
   ```

2. Start the frontend:

   ```bash
   cd frontend
   streamlit run app.py
   ```

3. Test authentication:
   - Click "Sign In / Sign Up" in the sidebar
   - Create a test account
   - Verify you can sign in

## Step 7: Migrate Existing Data (Optional)

If you have existing SQLite data to migrate:

```bash
cd backend
python scripts/migrate_to_supabase.py
```

## Features Enabled

With Supabase integration, you now have:

- ✅ Email/Password authentication
- ✅ OAuth authentication (Google, GitHub, etc.)
- ✅ Magic link (passwordless) authentication
- ✅ User profiles and preferences
- ✅ Secure file storage
- ✅ Real-time updates (conversations, messages)
- ✅ Row-level security (users can only access their own data)

## Troubleshooting

### Authentication not working

1. Check that Supabase URL and keys are correct
2. Verify RLS policies are enabled
3. Check browser console for errors

### Storage uploads failing

1. Verify storage buckets are created
2. Check storage policies are set correctly
3. Ensure user is authenticated

### Real-time not working

1. Check that Realtime is enabled in Supabase dashboard
2. Verify you're subscribed to the correct channels
3. Check network connectivity

## Security Notes

- Never expose `service_role_key` in frontend code
- Always use RLS policies for data access
- Use signed URLs for private file access
- Regularly rotate API keys

## Next Steps

- Customize user profile fields
- Add more OAuth providers
- Configure email templates
- Set up database backups
- Enable audit logging
