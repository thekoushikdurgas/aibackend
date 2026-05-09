-- Setup Supabase Storage Buckets
-- Run this SQL in your Supabase SQL Editor

-- Create storage buckets
INSERT INTO storage.buckets (id, name, public)
VALUES
    ('user-uploads', 'user-uploads', false),
    ('user-avatars', 'user-avatars', true),
    ('rag-documents', 'rag-documents', false)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for user-uploads (private)
DROP POLICY IF EXISTS "Users can upload own files" ON storage.objects;
CREATE POLICY "Users can upload own files"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'user-uploads' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

DROP POLICY IF EXISTS "Users can view own files" ON storage.objects;
CREATE POLICY "Users can view own files"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'user-uploads' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

DROP POLICY IF EXISTS "Users can delete own files" ON storage.objects;
CREATE POLICY "Users can delete own files"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'user-uploads' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Storage policies for user-avatars (public read, private write)
DROP POLICY IF EXISTS "Anyone can view avatars" ON storage.objects;
CREATE POLICY "Anyone can view avatars"
    ON storage.objects FOR SELECT
    USING (bucket_id = 'user-avatars');

DROP POLICY IF EXISTS "Users can upload own avatar" ON storage.objects;
CREATE POLICY "Users can upload own avatar"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'user-avatars' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

DROP POLICY IF EXISTS "Users can delete own avatar" ON storage.objects;
CREATE POLICY "Users can delete own avatar"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'user-avatars' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

-- Storage policies for rag-documents (private)
DROP POLICY IF EXISTS "Users can upload own documents" ON storage.objects;
CREATE POLICY "Users can upload own documents"
    ON storage.objects FOR INSERT
    WITH CHECK (
        bucket_id = 'rag-documents' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

DROP POLICY IF EXISTS "Users can view own documents" ON storage.objects;
CREATE POLICY "Users can view own documents"
    ON storage.objects FOR SELECT
    USING (
        bucket_id = 'rag-documents' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

DROP POLICY IF EXISTS "Users can delete own documents" ON storage.objects;
CREATE POLICY "Users can delete own documents"
    ON storage.objects FOR DELETE
    USING (
        bucket_id = 'rag-documents' AND
        auth.uid()::text = (storage.foldername(name))[1]
    );

