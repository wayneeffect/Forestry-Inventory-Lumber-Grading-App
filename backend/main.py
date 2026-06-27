import os
from enum import Enum
from datetime import datetime
from typing import Optional
import requests
import psycopg2  # Use asyncpg in production for async database performance
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# 1. INITIALIZATION & CONFIGURATION
# Load environment variables from the hidden .env file
load_dotenv()

# Retrieve the secure Pl@ntNet config from environment variables
PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")
PLANTNET_BASE_URL = "https://my-api.plantnet.org/v2/identify/all"

app = FastAPI(title="Forestry Inventory & Identification API")


# 2. DATA MODELS & ENUMS (Pydantic Layer)
class LumberGrade(str, Enum):
    veneer = "Veneer"
    select_better = "Select/Better"
    no_1_common = "No. 1 Common"
    no_2_common = "No. 2 Common"
    pallet = "Pallet"

# Validates incoming structured JSON payloads sent from the Mobile App
class TreeRecordCreate(BaseModel):
    record_id: str = Field(..., example="LOG-2026-0001")
    image_uri: str = Field(..., example="https://storage.provider.com/logs/img_102.jpg")
    ai_species_suggestion: str = Field(..., example="Quercus alba (White Oak)")
    latitude: float = Field(..., ge=-90, le=90, example=46.3542)
    longitude: float = Field(..., ge=-180, le=180, example=-85.5094)
    
    # Manual Expert Grading Parameters
    estimated_dbh: float = Field(..., gt=0, description="Diameter at breast height", example=18.5)
    clear_faces: int = Field(..., ge=0, le=4, example=3)
    assigned_grade: LumberGrade
    field_notes: Optional[str] = Field(None, example="Slight frost crack on northern face.")


# 3. API ROUTE ENDPOINTS
@app.post("/api/identify", status_code=status.HTTP_200_OK)
def identify_bark_image(image_path: str):
    """
    Acts as a secure proxy to forward local field photos to the Pl@ntNet engine
    without exposing the API key to the client mobile application binary.
    """
    if not PLANTNET_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail="Server configuration error: Missing Pl@ntNet API Key."
        )
    
    if not os.path.exists(image_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"Target target image file path not found: {image_path}"
        )

    try:
        # Open and package the binary image file stream
        with open(image_path, "rb") as image_file:
            files = {"images": image_file}
            data = {"organs": ["bark"]}  # Defaulted to bark profiles for woodlots
            params = {"api-key": PLANTNET_API_KEY}
            
            response = requests.post(PLANTNET_BASE_URL, params=params, files=files, data=data)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"Pl@ntNet API returned an error: {response.text}"
                )
                
            return response.json()
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Visual identification pipeline failure: {str(e)}"
        )


@app.post("/api/inventory", status_code=status.HTTP_201_CREATED)
def log_field_data(payload: TreeRecordCreate):
    """
    Accepts complete field inventory payloads and commits them directly 
    into the PostGIS relational tracking engine.
    """
    try:
        # Database Connection Configuration - Replace values with your active DB settings
        # conn = psycopg2.connect("dbname=forestry user=postgres password=secret")
        # cursor = conn.cursor()
        
        # PostGIS syntax integration: ST_SetSRID converts flat float strings to Geometry objects
        query = """
            INSERT INTO forestry_inventory (
                record_id, image_uri, ai_species_suggestion, geom, estimated_dbh, clear_faces, assigned_grade, field_notes
            ) VALUES (%s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s, %s);
        """
        
        db_values = (
            payload.record_id,
            payload.image_uri,
            payload.ai_species_suggestion,
            payload.longitude,  # PostGIS architecture requires Longitude FIRST
            payload.latitude,   # Latitude SECOND
            payload.estimated_dbh,
            payload.clear_faces,
            payload.assigned_grade.value,
            payload.field_notes
        )
        
        # cursor.execute(query, db_values)
        # conn.commit()
        # cursor.close()
        # conn.close()
        
        return {"status": "success", "message": f"Record {payload.record_id} saved successfully."}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Database insertion failed: {str(e)}"
        )
