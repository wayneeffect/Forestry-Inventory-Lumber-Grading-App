-- Enable the PostGIS spatial extension
CREATE EXTENSION IF NOT EXISTS postgis;

-- Create an explicit ENUM type for the lumber grading system
CREATE TYPE lumber_grade AS ENUM (
    'Veneer', 
    'Select/Better', 
    'No. 1 Common', 
    'No. 2 Common', 
    'Pallet'
);

-- Create the core forestry inventory table
CREATE TABLE forestry_inventory (
    record_id VARCHAR(50) PRIMARY KEY,
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    image_uri TEXT NOT NULL,
    ai_species_suggestion VARCHAR(255),
    
    -- Spatial column: Stores coordinates using standard WGS 84 (SRID 4326)
    geom GEOMETRY(Point, 4326),
    
    -- Manual Input Fields
    estimated_dbh NUMERIC(5, 2), -- Supports values like 124.50 inches/cm
    clear_faces INTEGER CHECK (clear_faces BETWEEN 0 AND 4),
    assigned_grade lumber_grade NOT NULL,
    field_notes TEXT
);

-- Create a spatial index for lightning-fast mapping and geographic queries
CREATE INDEX idx_forestry_geom ON forestry_inventory USING gist(geom);
