-- ============================================
-- Database Initialization Script
-- Version: 1.0.0
-- Description: Creates tables and seed data for k8s-platform demo
-- Author: Generated for production-grade deployment
-- ============================================

-- ============================================
-- TABLE: items
-- Description: Sample items for demo application
-- ============================================
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,  -- Prevent duplicate names
    description TEXT,  -- Optional description
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_items_name_length CHECK (LENGTH(name) > 0 AND LENGTH(name) <= 100)
);

-- Index for frequent name lookups (used in /data endpoint)
CREATE INDEX IF NOT EXISTS idx_items_name ON items(name);

-- Index for timestamp queries
CREATE INDEX IF NOT EXISTS idx_items_created_at ON items(created_at DESC);

-- ============================================
-- TABLE: football_clubs
-- Description: Football club information with country
-- ============================================
CREATE TABLE IF NOT EXISTS football_clubs (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT NOT NULL,
    founded_year INTEGER,  -- Optional founding year
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    -- Constraints
    CONSTRAINT uq_club_name_country UNIQUE(name, country),  -- Same club name allowed in different countries
    CONSTRAINT chk_name_length CHECK (LENGTH(name) > 0 AND LENGTH(name) <= 100),
    CONSTRAINT chk_country_length CHECK (LENGTH(country) > 0 AND LENGTH(country) <= 50),
    CONSTRAINT chk_founded_year CHECK (founded_year IS NULL OR (founded_year >= 1800 AND founded_year <= EXTRACT(YEAR FROM CURRENT_DATE)))
);

-- Indexes for frequent queries (used in /footballClub endpoint)
CREATE INDEX IF NOT EXISTS idx_football_clubs_name ON football_clubs(name);
CREATE INDEX IF NOT EXISTS idx_football_clubs_country ON football_clubs(country);
CREATE INDEX IF NOT EXISTS idx_football_clubs_created_at ON football_clubs(created_at DESC);

-- ============================================
-- FUNCTION: Update timestamp trigger
-- Description: Automatically update updated_at on row modifications
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for automatic timestamp updates
DROP TRIGGER IF EXISTS update_items_updated_at ON items;
CREATE TRIGGER update_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_football_clubs_updated_at ON football_clubs;
CREATE TRIGGER update_football_clubs_updated_at
    BEFORE UPDATE ON football_clubs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- SEED DATA: items
-- Description: Initial sample data for testing
-- ============================================
INSERT INTO items (name, description) VALUES
    ('alpha', 'First item in the Greek alphabet'),
    ('beta', 'Second item in the Greek alphabet'),
    ('gamma', 'Third item in the Greek alphabet'),
    ('delta', 'Fourth item in the Greek alphabet'),
    ('epsilon', 'Fifth item in the Greek alphabet')
ON CONFLICT (name) DO NOTHING;  -- Safe to re-run - skip if exists

-- ============================================
-- SEED DATA: football_clubs
-- Description: Initial football club data
-- ============================================
INSERT INTO football_clubs (name, country, founded_year) VALUES
    ('Manchester United', 'England', 1878),
    ('Real Madrid', 'Spain', 1902),
    ('Barcelona', 'Spain', 1899),
    ('Bayern Munich', 'Germany', 1900),
    ('Juventus', 'Italy', 1897),
    ('Liverpool', 'England', 1892),
    ('AC Milan', 'Italy', 1899),
    ('Ajax', 'Netherlands', 1900),
    ('Paris Saint-Germain', 'France', 1970),
    ('Manchester City', 'England', 1880)
ON CONFLICT (name, country) DO NOTHING;  -- Safe to re-run - skip if exists

-- ============================================
-- VERIFICATION QUERIES
-- Description: Queries to verify initialization
-- ============================================
-- Uncomment to run verification
-- SELECT COUNT(*) as item_count FROM items;
-- SELECT COUNT(*) as club_count FROM football_clubs;
-- SELECT tablename, indexname FROM pg_indexes WHERE schemaname = 'public';

-- ============================================
-- GRANTS (Optional)
-- Description: Grant permissions to application user
-- Note: Uncomment if using restricted database user
-- ============================================
-- GRANT SELECT, INSERT, UPDATE, DELETE ON items TO demo_user;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON football_clubs TO demo_user;
-- GRANT USAGE, SELECT ON SEQUENCE items_id_seq TO demo_user;
-- GRANT USAGE, SELECT ON SEQUENCE football_clubs_id_seq TO demo_user;
-- GRANT EXECUTE ON FUNCTION update_updated_at_column() TO demo_user;

-- ============================================
-- End of initialization script
-- Version: 1.0.0
-- ============================================
