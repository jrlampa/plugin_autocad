import os
import sqlite3
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any
from backend.core.logger import get_logger

logger = get_logger(__name__)

class ExportService:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    def export_project_to_geojson(self, project_id: str) -> Path:
        """
        Exports a project as a standard GeoJSON FeatureCollection.
        """
        logger.info(f"Exporting project {project_id} to GeoJSON.")
        conn = sqlite3.connect(self.db_path)
        try:
            # Query all features for the project
            rows = conn.execute("""
                SELECT feature_type, layer, name, highway, width_m, color, elevation, slope, original_geojson_properties, coords_xy
                FROM CadFeatures WHERE project_id = ?
            """, (project_id,)).fetchall()
            
            features = []
            for row in rows:
                f_type, layer, name, highway, width, color, elev, slope, props_json, coords_json = row
                
                # Parse strings/JSON
                import json
                props = json.loads(props_json) if props_json else {}
                coords = json.loads(coords_json) if coords_json else []
                
                # Enrich properties
                props.update({
                    "sisrua:feature_type": f_type,
                    "sisrua:layer": layer,
                    "sisrua:name": name,
                    "sisrua:highway": highway,
                    "sisrua:width_m": width,
                    "sisrua:color": color,
                    "sisrua:elevation": elev,
                    "sisrua:slope": slope
                })
                
                features.append({
                    "type": "Feature",
                    "properties": props,
                    "geometry": {
                        "type": "LineString" if f_type == "Polyline" else "Point",
                        "coordinates": coords
                    }
                })
            
            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "project_id": project_id,
                    "exported_at": str(Path().stat().st_mtime) # Placeholder
                }
            }
            
            temp_dir = Path(tempfile.mkdtemp())
            export_file = temp_dir / f"sisrua_{project_id}.geojson"
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(geojson, f, indent=2)
                
            return export_file
        finally:
            conn.close()

    def export_project_to_geopackage(self, project_id: str) -> Path:
        """
        Generates a GPKG package by copying the DB and ensuring metadata is purged 
        for everything except the requested project.
        """
        logger.info(f"Refining GeoPackage export for project {project_id}.")
        
        temp_dir = Path(tempfile.mkdtemp())
        export_file = temp_dir / f"sisrua_{project_id}.gpkg"
        
        # Copy original DB
        shutil.copy2(self.db_path, export_file)
        
        conn = sqlite3.connect(export_file)
        try:
            # purging unrelated projects from the export file to save space and privacy
            conn.execute("DELETE FROM CadFeatures WHERE project_id != ?", (project_id,))
            conn.execute("DELETE FROM Projects WHERE project_id != ?", (project_id,))
            
            # Setup GPKG Metadata
            project_info = conn.execute(
                "SELECT project_name, crs_out FROM Projects WHERE project_id = ?", 
                (project_id,)
            ).fetchone()
            
            if not project_info:
                raise Exception(f"Project {project_id} not found.")
                
            project_name, crs_out = project_info
            srs_id = 4326
            if crs_out and "EPSG:" in crs_out:
                try: srs_id = int(crs_out.split(":")[1])
                except: pass

            # Register tables
            conn.execute("""
                INSERT OR REPLACE INTO gpkg_contents 
                (table_name, data_type, identifier, description, srs_id)
                VALUES (?, ?, ?, ?, ?)
            """, ("CadFeatures", "features", project_id, f"sisRUA Project: {project_name}", srs_id))
            
            conn.execute("""
                INSERT OR REPLACE INTO gpkg_geometry_columns 
                (table_name, column_name, geometry_type_name, srs_id, z, m)
                VALUES (?, ?, ?, ?, 1, 0)
            """, ("CadFeatures", "coords_xy", "GEOMETRY", srs_id, 1, 0))
            
            conn.commit()
            # Vacum to shrink file
            conn.execute("VACUUM")
        finally:
            conn.close()
            
        return export_file
