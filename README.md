# Forestry Inventory & Lumber Grading App 🌲📐

A mobile-first engineering solution designed for forestry professionals, loggers, and lumber graders to automate timber cruising, real-time botanical identification, and precise spatial telemetry logging in the field.

---

## 🛠️ Core Technical Pillars

### 1. Visual Identification Layer
* **The Challenge:** Google Lens lacks a public API and is too generalized for commercial forestry.
* **The Solution:** Integrated **Pl@ntNet API** on the backend. Field workers capture high-resolution images of bark structures, leaf formations, or log cross-sections, returning precise, research-backed botanical and common species mappings.

### 2. Geolocation & Spatial Mapping Layer
* **The Challenge:** Image processing pipelines cannot inherently resolve physical capture coordinates.
* **The Solution:** Leverages native device hardware GPS chipsets (via Android's `FusedLocationProviderClient` / iOS `CoreLocation`). The exact coordinate strings are captured synchronously on camera shutter release and bound permanently to the log payload.
* **GIS Output:** Data points are modeled as spatial entities and are exportable via dynamic **Keyhole Markup Language (.KML)** for instant mapping in Google Earth Pro or QGIS.

### 3. Structural Lumber Grading Layer
* **The Challenge:** Visual computer vision models cannot reliably grade inner wood quality, internal rot, or grain integrity.
* **The Solution:** A custom field data-entry engine combining automated sensor metrics with manual input parameter matrices (`Estimated_DBH`, `Clear_Faces`, and architectural wood scaling).

---

## 📂 Repository Architecture

```text
forestry-inventory-app/
├── .gitignore            # Suppresses Python environments, variables, and binaries
├── README.md             # Project documentation
├── database/
│   └── schema.sql        # PostgreSQL + PostGIS spatial schema initialization
├── backend/
│   ├── main.py           # FastAPI server, Pydantic models, and API routing
│   ├── kml_exporter.py   # Python GIS KML compilation utility
│   └── .env              # Hidden environment variables (Pl@ntNet API Key)
└── mobile_app/
    └── lib/
        └── field_logger.dart # Cross-platform Flutter Field UI layout

```

---

## 🐘 Data Model & Schema (PostGIS)

The application stores all transactional entries inside a relational **PostgreSQL** instance enhanced with the **PostGIS** spatial geometry extension to allow for lightning-fast geographic indexing (`GIST`).

### Database Fields

* **Record_ID:** Unique alphanumeric transaction string (`PRIMARY KEY`).
* **Timestamp:** High-resolution capture date and time with precise timezone support.
* **Image_URI:** Persistent local filepath or cloud storage reference identifier.
* **AI_Species_Suggestion:** Optimal botanical taxonomy string returned from the API handler.
* **geom:** Coordinate object using the standard WGS 84 spatial reference identifier (`SRID 4326`).
* **Estimated_DBH:** Diameter at breast height (numeric tracking).
* **Clear_Faces:** Integer checking constraints bounded explicitly between `0 and 4`.
* **Assigned_Grade:** Enumerated category allocation (`Veneer`, `Select/Better`, `No. 1 Common`, `No. 2 Common`, `Pallet`).
* **Field_Notes:** Variable character text block for capturing visible structural defects (e.g., frost cracks, seams, sap-rot).

---

## ⚙️ Quickstart & Local Environment Setup

### Prerequisites

* Python 3.10+
* Flutter SDK (3.x+)
* PostgreSQL with PostGIS extension enabled

### 1. Backend Configuration

Navigate to the backend directory, spin up your virtual environment, and install your system dependencies:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
pip install -r requirements.txt

```

Create a `.env` file in the `backend/` directory:

```text
PLANTNET_API_KEY=your_free_plantnet_developer_token_here
DATABASE_URL=postgresql://postgres:secret@localhost:5432/forestry

```

Run the API service using Uvicorn:

```bash
uvicorn main:app --reload

```

### 2. Frontend Execution

Ensure you have a target device attached, then run the compilation loop from the mobile directory:

```bash
cd ../mobile_app
flutter pub get
flutter run

```
