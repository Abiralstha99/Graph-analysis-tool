-- MRG Labs Graphing App - Database Setup Script
-- Run this script to initialize the database for authentication

-- Create database
CREATE DATABASE IF NOT EXISTS mrg_labs_db;

USE mrg_labs_db;

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create graphs table
CREATE TABLE IF NOT EXISTS graphs (
    graph_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    baseline_filename VARCHAR(255),
    sample_filename VARCHAR(255),
    generated_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_created_at (created_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- analyses: one row per authenticated analysis request
CREATE TABLE IF NOT EXISTS analyses (
    id                CHAR(36)     PRIMARY KEY,
    user_id           INT          NOT NULL,
    scoring_method    VARCHAR(20)  NOT NULL DEFAULT 'hybrid',
    zone_weights      JSON,
    status            ENUM('queued', 'processing', 'completed', 'failed', 'cancelled')
                                   NOT NULL DEFAULT 'queued',
    baseline_filename VARCHAR(255) NOT NULL,
    sample_filenames  JSON         NOT NULL,
    scores            JSON,
    deviation_data    JSON,
    summary           JSON,
    error_message     TEXT,
    created_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP    DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    completed_at      TIMESTAMP    NULL,
    INDEX idx_analyses_user_id (user_id),
    INDEX idx_analyses_status (status),
    INDEX idx_analyses_created_at (created_at),
    INDEX idx_analyses_updated_at (updated_at),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- jobs: process-local background job tracking
CREATE TABLE IF NOT EXISTS jobs (
    id            CHAR(36)    PRIMARY KEY,
    analysis_id   CHAR(36)    NOT NULL,
    user_id       INT         NOT NULL,
    status        ENUM('queued', 'processing', 'completed', 'failed', 'cancelled')
                             NOT NULL DEFAULT 'queued',
    attempt       INT         NOT NULL DEFAULT 0,
    error_message TEXT,
    created_at    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP   DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_jobs_analysis_id (analysis_id),
    INDEX idx_jobs_user_id (user_id),
    INDEX idx_jobs_status (status),
    INDEX idx_jobs_updated_at (updated_at),
    FOREIGN KEY (analysis_id) REFERENCES analyses(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: Create a test user (password: testpass123)
-- Password hash generated using bcrypt
-- INSERT INTO users (username, password) VALUES 
-- ('testuser', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5ygDXLhXO9qCy');

-- Display table structures
DESCRIBE users;
DESCRIBE graphs;
DESCRIBE analyses;
DESCRIBE jobs;

-- Display success message
SELECT 'Database setup complete!' AS status;
