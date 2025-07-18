-- Initialize Spinscribe database
CREATE DATABASE IF NOT EXISTS spinscribe;
CREATE USER IF NOT EXISTS spinscribe_user WITH PASSWORD 'spinscribe_password';
GRANT ALL PRIVILEGES ON DATABASE spinscribe TO spinscribe_user;

-- Enable necessary extensions
\c spinscribe;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";  -- For vector embeddings if using pgvector
