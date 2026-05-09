-- Storage buckets for file uploads (names match defaults in app/config.py Settings).
-- Run as postgres superuser or storage admin after Storage API has initialized storage schema.

INSERT INTO storage.buckets (id, name, public)
VALUES
    ('user-uploads', 'user-uploads', false),
    ('user-avatars', 'user-avatars', true),
    ('rag-documents', 'rag-documents', false)
ON CONFLICT (id) DO NOTHING;
