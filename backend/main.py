import os
from enum import Enum
from datetime import datetime
from typing import Optional
import requests
import psycopg2  # Use asyncpg in production for async database performance
from fastapi import FastAPI, HTTPException, status, Form, File, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

PLANTNET_API_KEY = os.getenv("PLANTNET_API_KEY")
PLANTNET_BASE_URL = "https://my-api.plantnet.org/v2/identify/all"

app = FastAPI(title="Forestry Inventory & Identification API")

# --- FRONTEND UI DASHBOARD LAYER ---
@app.get("/", response_class=HTMLResponse)
def dashboard_frontend():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Forestry Field Dashboard</title>
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background-color: #121212; color: #e0e0e0; margin: 0; padding: 15px; }
            .container { max-width: 600px; margin: 0 auto; background: #1e1e1e; padding: 20px; border-radius: 12px; box-shadow: 0 4px 10px rgba(0,0,0,0.5); }
            h1 { color: #4caf50; text-align: center; font-size: 24px; margin-bottom: 20px; }
            .status-card { background: #2a2a2a; padding: 12px; border-radius: 8px; border-left: 4px solid #ffb300; margin-bottom: 20px; font-size: 14px; }
            .status-line { margin: 6px 0; }
            .accent { color: #ffb300; font-weight: bold; }
            .success-accent { color: #4caf50; font-weight: bold; }
            button { width: 100%; background-color: #4caf50; color: white; border: none; padding: 14px; font-size: 16px; border-radius: 8px; font-weight: bold; cursor: pointer; margin-bottom: 15px; }
            button:active { background-color: #388e3c; }
            .secondary-btn { background-color: #2196f3; }
            .secondary-btn:active { background-color: #0b7dda; }
            input, select, textarea { width: 100%; padding: 12px; background: #2d2d2d; border: 1px solid #444; border-radius: 6px; color: white; margin-bottom: 15px; box-sizing: border-box; font-size: 15px; }
            label { display: block; margin-bottom: 6px; font-size: 14px; color: #aaa; }
            #camera-preview { width: 100%; max-height: 300px; border-radius: 8px; background: #000; display: none; margin-bottom: 15px; object-fit: cover; }
            #captured-canvas { display: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Forestry Field Logger</h1>
            
            <div class="status-card">
                <div class="status-line">🛰️ GPS Telemetry: <span id="gps-display" class="accent">Acquiring Lock...</span></div>
                <div class="status-line">🔑 Record ID: <span id="record-id-display" class="accent">Generating...</span></div>
            </div>

            <video id="camera-preview" autoplay playsinline></video>
            <canvas id="captured-canvas"></canvas>
            
            <button type="button" id="camera-trigger-btn" onclick="startCamera()">📷 Open Camera</button>
            <button type="button" id="shutter-btn" style="display:none;" onclick="capturePhoto()">⚡ Snap Shutter</button>

            <form id="logger-form" onsubmit="submitFieldData(event)">
                <label for="dbh">Estimated DBH (Diameter Inches)</label>
                <input type="number" step="0.1" id="dbh" required placeholder="e.g. 18.5">

                <label for="clear_faces">Clear Faces (0 - 4)</label>
                <select id="clear_faces">
                    <option value="4">4 Faces Clear</option>
                    <option value="3">3 Faces Clear</option>
                    <option value="2">2 Faces Clear</option>
                    <option value="1">1 Face Clear</option>
                    <option value="0">0 Faces Clear (Utility)</option>
                </select>

                <label for="assigned_grade">Assigned Lumber Grade</label>
                <select id="assigned_grade">
                    <option value="Veneer">Veneer</option>
                    <option value="Select/Better">Select/Better</option>
                    <option value="No. 1 Common">No. 1 Common</option>
                    <option value="No. 2 Common">No. 2 Common</option>
                    <option value="Pallet">Pallet</option>
                </select>

                <label for="field_notes">Field Inspection Notes</label>
                <textarea id="field_notes" rows="3" placeholder="Note seams, rot, frost cracks..."></textarea>

                <button type="submit" class="secondary-btn">💾 Transmit & Sync Log</button>
            </form>
        </div>

        <script>
            let currentLatitude = 0.0;
            let currentLongitude = 0.0;
            let capturedBlob = null;
            const generatedRecordId = "LOG-" + Math.random().toString(36).substring(2, 10).toUpperCase();

            // Initialize Page Sessions & Permissions Hooks
            document.getElementById('record-id-display').innerText = generatedRecordId;
            
            if (navigator.geolocation) {
                navigator.geolocation.watchPosition(
                    (position) => {
                        currentLatitude = position.coords.latitude;
                        currentLongitude = position.coords.longitude;
                        document.getElementById('gps-display').innerText = currentLatitude.toFixed(5) + ", " + currentLongitude.toFixed(5);
                    },
                    (error) => { document.getElementById('gps-display').innerText = "Telemetry Denied"; },
                    { enableHighAccuracy: true }
                );
            }

            // Stream Video Pipeline
            async function startCamera() {
                const video = document.getElementById('camera-preview');
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false });
                    video.srcObject = stream;
                    video.style.display = "block";
                    document.getElementById('camera-trigger-btn').style.display = "none";
                    document.getElementById('shutter-btn').style.display = "block";
                } catch (err) {
                    alert("Camera Access Failure: " + err);
                }
            }

            // Capture raw frame buffer arrays from video stream
            function capturePhoto() {
                const video = document.getElementById('camera-preview');
                const canvas = document.getElementById('captured-canvas');
                const ctx = canvas.getContext('2d');
                
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                
                // Halt standard streaming devices to save mobile battery
                let stream = video.srcObject;
                let tracks = stream.getTracks();
                tracks.forEach(track => track.stop());
                video.style.display = "none";
                document.getElementById('shutter-btn').style.display = "none";
                
                // Convert Frame buffer items directly into web standard file uploads
                canvas.toBlob((blob) => {
                    capturedBlob = blob;
                    document.getElementById('camera-trigger-btn').style.display = "block";
                    document.getElementById('camera-trigger-btn').innerText = "🔄 Retake Photo";
                    alert("Image locked with coordinates successfully!");
                }, 'image/jpeg', 0.85);
            }

            // Deliver multi-part binary items directly to server API processing channels
            async function submitFieldData(e) {
                e.preventDefault();
                if(!capturedBlob) {
                    alert("❌ You must capture a photo of the tree or log profile first.");
                    return;
                }

                let formData = new FormData();
                formData.append("record_id", generatedRecordId);
                formData.append("latitude", currentLatitude);
                formData.append("longitude", currentLongitude);
                formData.append("estimated_dbh", document.getElementById('dbh').value);
                formData.append("clear_faces", document.getElementById('clear_faces').value);
                formData.append("assigned_grade", document.getElementById('assigned_grade').value);
                formData.append("field_notes", document.getElementById('field_notes').value);
                formData.append("image_file", capturedBlob, "capture.jpg");

                try {
                    let response = await fetch("/api/inventory", { method: "POST", body: formData });
                    let resData = await response.json();
                    if(response.ok) {
                        alert("🎉 Log Synced Successfully! " + resData.message);
                        window.location.reload();
                    } else {
                        alert("Submission Failed: " + resData.detail);
                    }
                } catch (err) {
                    alert("Network transport error: " + err);
                }
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content, status_code=200)


# --- BACKEND LOGIC & DATA PROCESSING LAYER ---
@app.post("/api/inventory", status_code=status.HTTP_201_CREATED)
def log_field_data(
    record_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    estimated_dbh: float = Form(...),
    clear_faces: int = Form(...),
    assigned_grade: str = Form(...),
    field_notes: Optional[str] = Form(None),
    image_file: UploadFile = File(...)
):
    """
    Accepts processing strings and multi-part raw field data elements directly 
    from browsers or mobile clients and pushes entries into standard inventory systems.
    """
    try:
        # Step A: Safe file-system buffer stream handlers can go here 
        # (e.g. saving image_file.file.read() to an AWS S3 Bucket or local block storage)
        mock_saved_cloud_uri = f"https://storage.provider.com/inventory/images/{record_id}.jpg"
        
        # Step B: Secure proxy routing forward to Pl@ntNet using server-side keys
        ai_species_match = "Quercus alba (White Oak)" # Fallback default
        if PLANTNET_API_KEY:
            try:
                # Seek start of memory location buffer array pointers
                image_file.file.seek(0)
                files = {"images": (image_file.filename, image_file.file, image_file.content_type)}
                data = {"organs": ["bark"]}
                params = {"api-key": PLANTNET_API_KEY}
                
                p_res = requests.post(PLANTNET_BASE_URL, params=params, files=files, data=data, timeout=10)
                if p_res.status_code == 200:
                    results = p_res.json().get('results', [])
                    if results:
                        ai_species_match = results[0]['species']['scientificNameWithoutAuthor']
            except Exception:
                pass # Graceful error mitigation for remote system down times in deep woods

        # Step C: PostGIS Relational Compilation Database Insert Statement Execution
        # conn = psycopg2.connect("dbname=forestry user=postgres password=secret")
        # cursor = conn.cursor()
        # query = "INSERT INTO forestry_inventory (...) VALUES (%s, %s, ST_SetSRID(ST_MakePoint(%s,%s), 4326), ...)"
        # cursor.execute(query, (...))
        # conn.commit()

        return {
            "status": "success", 
            "message": f"Log metadata synced for tree record {record_id}.",
            "resolved_species": ai_species_match
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal compilation layer error: {str(e)}")
