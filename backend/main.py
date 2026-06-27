from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from datetime import datetime
from typing import Optional
from enum import Enum
import psycopg2 # Use asyncpg in production for async database performance

app = FastAPI(title="Forestry Inventory API")

# Define the allowed grading scale using Python Enums
class LumberGrade(str, Enum):
    veneer = "Veneer"
    select_better = "Select/Better"
    no_1_common = "No. 1 Common"
    no_2_common = "No. 2 Common"
    pallet = "Pallet"

# Pydantic Model to validate incoming data payload from the Mobile App
class TreeRecordCreate(BaseModel):
    record_id: str = Field(..., example="LOG-2026-0001")
    image_uri: str = Field(..., example="https://storage.provider.com/logs/img_102.jpg")
    ai_species_suggestion: str = Field(..., example="Quercus alba (White Oak)")
    latitude: float = Field(..., ge=-90, le=90, example=45.12345)
    longitude: float = Field(..., ge=-180, le=180, example=-93.54321)
    
    # Manual Input
    estimated_dbh: float = Field(..., gt=0, description="Diameter at breast height", example=18.5)
    clear_faces: int = Field(..., ge=0, le=4, example=3)
    assigned_grade: LumberGrade
    field_notes: Optional[str] = Field(None, example="Slight frost crack on northern face.")

@app.post("/api/inventory", status_code=status.HTTP_201_CREATED)
def log_field_data(payload: TreeRecordCreate):
    try:
        # Mocking database connection - replace with your actual DB pool credentials
        # conn = psycopg2.connect("dbname=forestry user=postgres password=secret")
        # cursor = conn.cursor()
        
        # Convert raw Lat/Long floats into a PostGIS Point geometry object string
        # ST_SetSRID(ST_MakePoint(Long, Lat), 4326)
        query = """
            INSERT INTO forestry_inventory (
                record_id, image_uri, ai_species_suggestion, geom, estimated_dbh, clear_faces, assigned_grade, field_notes
            ) VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s);
        """
        
        db_values = (
            payload.record_id,
            payload.image_uri,
            payload.ai_species_suggestion,
            payload.longitude, # PostGIS expects Longitude FIRST
            payload.latitude,  # Latitude SECOND
            payload.estimated_dbh,
            payload.clear_faces,
            payload.assigned_grade.value,
            payload.field_notes
        )
        
        # cursor.execute(query, db_values)
        # conn.commit()
        
        return {"status": "success", "message": f"Record {payload.record_id} saved successfully."}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database insertion failed: {str(e)}")
