-- ClickHouse initialization script for Langfuse
-- This script creates the necessary database and tables for Langfuse tracing

-- Create the langfuse database if it doesn't exist
CREATE DATABASE IF NOT EXISTS langfuse;

-- Switch to the langfuse database
USE langfuse;

-- Create traces table optimized for low memory usage
CREATE TABLE IF NOT EXISTS traces (
    id String,
    name String,
    user_id String,
    metadata String,
    release String,
    version String,
    project_id String,
    public Bool,
    bookmarked Bool,
    tags Array(String),
    input String,
    output String,
    session_id String,
    created_at DateTime,
    updated_at DateTime,
    INDEX idx_project_id project_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_user_id user_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_session_id session_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_created_at created_at TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree()
ORDER BY (project_id, created_at)
SETTINGS index_granularity = 8192;

-- Create observations table for spans and generations
CREATE TABLE IF NOT EXISTS observations (
    id String,
    trace_id String,
    project_id String,
    type String,
    name String,
    start_time DateTime,
    end_time DateTime,
    parent_observation_id String,
    metadata String,
    input String,
    output String,
    model String,
    model_parameters String,
    prompt_tokens UInt32,
    completion_tokens UInt32,
    total_tokens UInt32,
    unit String,
    level String,
    status_message String,
    version String,
    created_at DateTime,
    updated_at DateTime,
    INDEX idx_trace_id trace_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_project_id project_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_type type TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_start_time start_time TYPE minmax GRANULARITY 1
)
ENGINE = MergeTree()
ORDER BY (project_id, start_time)
SETTINGS index_granularity = 8192;

-- Create scores table for evaluation metrics
CREATE TABLE IF NOT EXISTS scores (
    id String,
    trace_id String,
    observation_id String,
    project_id String,
    name String,
    value Float64,
    string_value String,
    comment String,
    created_at DateTime,
    updated_at DateTime,
    INDEX idx_trace_id trace_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_observation_id observation_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_project_id project_id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_name name TYPE bloom_filter(0.01) GRANULARITY 1
)
ENGINE = MergeTree()
ORDER BY (project_id, created_at)
SETTINGS index_granularity = 8192;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id String,
    name String,
    email String,
    created_at DateTime,
    updated_at DateTime,
    INDEX idx_id id TYPE bloom_filter(0.01) GRANULARITY 1
)
ENGINE = MergeTree()
ORDER BY (id)
SETTINGS index_granularity = 8192;

-- Create projects table
CREATE TABLE IF NOT EXISTS projects (
    id String,
    name String,
    created_at DateTime,
    updated_at DateTime,
    INDEX idx_id id TYPE bloom_filter(0.01) GRANULARITY 1
)
ENGINE = MergeTree()
ORDER BY (id)
SETTINGS index_granularity = 8192;

-- Create sessions table
CREATE TABLE IF NOT EXISTS sessions (
    id String,
    project_id String,
    created_at DateTime,
    updated_at DateTime,
    INDEX idx_id id TYPE bloom_filter(0.01) GRANULARITY 1,
    INDEX idx_project_id project_id TYPE bloom_filter(0.01) GRANULARITY 1
)
ENGINE = MergeTree()
ORDER BY (project_id, created_at)
SETTINGS index_granularity = 8192;

-- Grant permissions to langfuse user
GRANT ALL ON langfuse.* TO langfuse;