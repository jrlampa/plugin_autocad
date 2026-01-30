import sqlite3
from faker import Faker
import json
import uuid
from datetime import datetime
import random
import os

# Configuration
DB_PATH = os.path.join(os.environ.get("LOCALAPPDATA", "."), "sisRUA", "projects.db")
NUM_PROJECTS = 50
NUM_FEATURES_PER_PROJECT = random.randint(5, 20)

fake = Faker('pt_BR')  # Use Portuguese locale for realistic data

def init_db(conn):
    """Create tables if not exist based on Phase 1.5.1 schema."""
    cursor = conn.cursor()
    
    # Projects Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Projects (
        project_id TEXT PRIMARY KEY,
        project_name TEXT NOT NULL,
        creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
        crs_out TEXT
    )
    ''')
    
    # CadFeatures Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS CadFeatures (
        feature_id TEXT PRIMARY KEY,
        project_id TEXT NOT NULL,
        feature_type TEXT CHECK(feature_type IN ('Polyline', 'Point')),
        layer TEXT,
        name TEXT,
        highway TEXT,
        width_m REAL,
        coords_xy_json TEXT,
        insertion_point_xy_json TEXT, -- For Points
        block_name TEXT,              -- For Points
        block_filepath TEXT,          -- For Points
        rotation REAL,                -- For Points
        scale REAL,                   -- For Points
        original_geojson_properties_json TEXT,
        FOREIGN KEY(project_id) REFERENCES Projects(project_id)
    )
    ''')
    conn.commit()

def generate_projects(conn):
    cursor = conn.cursor()
    print(f"Generating {NUM_PROJECTS} projects...")

    for _ in range(NUM_PROJECTS):
        project_id = str(uuid.uuid4())
        project_name = f"Projeto {fake.city()} - {fake.street_name()}"
        creation_date = fake.date_time_between(start_date='-1y', end_date='now')
        crs_out = random.choice(["EPSG:31983", "EPSG:31984", "EPSG:32723"]) # Common SIRGAS zones
        
        cursor.execute(
            "INSERT INTO Projects (project_id, project_name, creation_date, crs_out) VALUES (?, ?, ?, ?)",
            (project_id, project_name, creation_date, crs_out)
        )
        
        # Generate features for this project
        num_feats = random.randint(5, 20)
        for _ in range(num_feats):
            feature_id = str(uuid.uuid4())
            ft_type = random.choice(["Polyline", "Point"])
            
            if ft_type == "Polyline":
                layer = "SISRUA_OSM_VIAS"
                name = fake.street_name()
                highway = random.choice(["residential", "tertiary", "secondary", "primary"])
                width_m = random.uniform(5.0, 12.0)
                
                # Generate random line coords (mocking projected xy)
                start_x = random.uniform(300000, 400000)
                start_y = random.uniform(7000000, 8000000)
                coords = [
                    [start_x, start_y],
                    [start_x + random.uniform(-100, 100), start_y + random.uniform(-100, 100)],
                    [start_x + random.uniform(-200, 200), start_y + random.uniform(-200, 200)]
                ]
                coords_json = json.dumps(coords)
                
                cursor.execute("""
                    INSERT INTO CadFeatures 
                    (feature_id, project_id, feature_type, layer, name, highway, width_m, coords_xy_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (feature_id, project_id, ft_type, layer, name, highway, width_m, coords_json))
                
            else: # Point
                layer = "SISRUA_OSM_PONTOS"
                block_name = random.choice(["POSTE", "ARVORE", "BANCO"])
                insertion_point = [random.uniform(300000, 400000), random.uniform(7000000, 8000000)]
                insertion_json = json.dumps(insertion_point)
                
                cursor.execute("""
                    INSERT INTO CadFeatures 
                    (feature_id, project_id, feature_type, layer, insertion_point_xy_json, block_name, rotation, scale)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (feature_id, project_id, ft_type, layer, insertion_json, block_name, 0.0, 1.0))

    conn.commit()
    print("Database seeded successfully.")

if __name__ == "__main__":
    # Ensure dir exists
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    print(f"Connecting to database: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        init_db(conn)
        generate_projects(conn)
    finally:
        conn.close()
