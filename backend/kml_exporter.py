import xml.etree.ElementTree as ET
from xml.dom import minidom
from fastapi import FastAPI, HTTPException, responses
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(title="Forestry GIS Export Engine")

# Dictionary assigning standard KML aabbggrr colors to structural wood grades
GRADE_COLORS = {
    "Veneer": "ff00aa00",         # Opique Dark Green
    "Select/Better": "ff00c8ff",  # Opaque Gold/Yellow
    "No. 1 Common": "ff0055ff",   # Opaque Dark Orange
    "No. 2 Common": "ff0000aa",   # Opaque Dark Red
    "Pallet": "ff0000ff"          # Opaque Neon Red
}

def generate_kml_tree(records):
    """
    Parses flat database dictionaries into structural OGC KML schemas.
    """
    # Initialize base KML elements with standard schemas
    kml = ET.Element("kml", xmlns="http://www.opengis.net/kml/2.2")
    document = ET.SubElement(kml, "Document")
    
    doc_name = ET.SubElement(document, "name")
    doc_name.text = "Active Stand Inventory & Lumber Grades"

    # 1. Create reusable styles for the mapping interface
    for grade, hex_color in GRADE_COLORS.items():
        style_id = f"style_{grade.replace('/', '_').replace(' ', '_').lower()}"
        style = ET.SubElement(document, "Style", id=style_id)
        icon_style = ET.SubElement(style, "IconStyle")
        
        color = ET.SubElement(icon_style, "color")
        color.text = hex_color
        
        scale = ET.SubElement(icon_style, "scale")
        scale.text = "1.3"
        
        icon = ET.SubElement(icon_style, "Icon")
        href = ET.SubElement(icon, "href")
        # Standard white push-pin asset used for hardware rendering coloration
        href.text = "http://maps.google.com/mapfiles/kml/pushpin/wht-pushpin.png"

    # 2. Map inventory records to individual geographic placemarks
    for log in records:
        placemark = ET.SubElement(document, "Placemark")
        
        p_name = ET.SubElement(placemark, "name")
        p_name.text = f"{log['ai_species_suggestion']} ({log['assigned_grade']})"
        
        # Format the description balloon using raw HTML syntax for cleaner layouts in GIS interfaces
        description = ET.SubElement(placemark, "description")
        description.text = f"""<![CDATA[
            <h3>Log Transaction ID: {log['record_id']}</h3>
            <hr />
            <p><strong>Species Match:</strong> {log['ai_species_suggestion']}</p>
            <p><strong>Lumber Grade:</strong> <span style="color:#00ff00; font-weight:bold;">{log['assigned_grade']}</span></p>
            <p><strong>Estimated DBH:</strong> {log['estimated_dbh']} in</p>
            <p><strong>Clear Faces:</strong> {log['clear_faces']}/4</p>
            <p><strong>Logged Time:</strong> {log['captured_at']}</p>
            <p><strong>Field Notes:</strong> {log['field_notes'] or 'None'}</p>
        ]]>"""
        
        # Attach the corresponding styling reference link
        style_key = f"#style_{log['assigned_grade'].replace('/', '_').replace(' ', '_').lower()}"
        style_url = ET.SubElement(placemark, "styleUrl")
        style_url.text = style_key
        
        # Define spatial coordinate payload using PostGIS numeric extractions
        point = ET.SubElement(placemark, "Point")
        coordinates = ET.SubElement(point, "coordinates")
        coordinates.text = f"{log['longitude']},{log['latitude']},0"

    # Output highly ordered and pretty-printed raw XML data strings
    xml_str = ET.tostring(kml, encoding="utf-8")
    parsed_xml = minidom.parseString(xml_str)
    return parsed_xml.toprettyxml(indent="  ")


@app.get("/api/gis/export-kml")
def export_inventory_kml():
    """
    API Endpoint: Queries PostGIS data rows, extracts telemetry points, 
    and returns a direct binary download stream of the generated KML file.
    """
    try:
        # DB Connection Stub - Replace with connection pool parameters
        conn = psycopg2.connect("dbname=forestry user=postgres password=secret", cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        
        # Extract explicit coordinates using PostGIS spatial processing expressions
        # ST_X extracts Longitude, ST_Y extracts Latitude from your Point object
        query = """
            SELECT 
                record_id, 
                captured_at, 
                ai_species_suggestion, 
                ST_X(geom) as longitude, 
                ST_Y(geom) as latitude, 
                estimated_dbh, 
                clear_faces, 
                assigned_grade, 
                field_notes 
            FROM forestry_inventory;
        """
        cursor.execute(query)
        db_records = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        if not db_records:
            raise HTTPException(status_code=404, detail="No forestry logs found in the database to export.")
        
        # Build file
        kml_content = generate_kml_tree(db_records)
        
        return responses.Response(
            content=kml_content,
            media_type="application/vnd.google-earth.kml+xml",
            headers={"Content-Disposition": "attachment; filename=stand_inventory.kml"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"GIS Engine compilation failure: {str(e)}")
