import os
import sqlite3
from pathlib import Path
from backend.core.logger import get_logger

logger = get_logger(__name__)

# Single source of truth for DB Path
DB_PATH = Path(os.environ.get("LOCALAPPDATA", ".")) / "sisRUA" / "projects.db"

def get_db_path() -> Path:
    # Ensure directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return DB_PATH

def init_geopackage(conn: sqlite3.Connection):
    """
    Initializes OGC GeoPackage metadata tables required for compatibility.
    """
    try:
        # 1. Spatial Reference System table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
                srs_name TEXT NOT NULL,
                srs_id INTEGER PRIMARY KEY,
                organization TEXT NOT NULL,
                organization_coordsys_id INTEGER NOT NULL,
                definition TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # 2. Add default WGS84 and Undefined SRS (Required by OGC)
        conn.execute("INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES (?, ?, ?, ?, ?, ?)",
                    ("Undefined Cartesian", -1, "NONE", -1, "undefined", "undefined"))
        conn.execute("INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES (?, ?, ?, ?, ?, ?)",
                    ("Undefined Geographic", 0, "NONE", 0, "undefined", "undefined"))
        conn.execute("INSERT OR IGNORE INTO gpkg_spatial_ref_sys VALUES (?, ?, ?, ?, ?, ?)",
                    ("WGS 84", 4326, "EPSG", 4326, 'GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563]],PRIMEM["Greenwich",0],UNIT["degree",0.0174532925199433]]', "World Geodetic System 1984"))

        # 3. Contents table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gpkg_contents (
                table_name TEXT PRIMARY KEY,
                data_type TEXT NOT NULL,
                identifier TEXT UNIQUE,
                description TEXT DEFAULT '',
                last_change DATETIME DEFAULT CURRENT_TIMESTAMP,
                min_x DOUBLE, min_y DOUBLE, max_x DOUBLE, max_y DOUBLE,
                srs_id INTEGER,
                FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
            )
        """)
        
        # 4. Geometry Columns table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
                table_name TEXT PRIMARY KEY,
                column_name TEXT NOT NULL,
                geometry_type_name TEXT NOT NULL,
                srs_id INTEGER NOT NULL,
                z INTEGER NOT NULL,
                m INTEGER NOT NULL,
                FOREIGN KEY (table_name) REFERENCES gpkg_contents(table_name),
                FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
            )
        """)
        
        conn.commit()
    except Exception as e:
        logger.error("gpkg_init_failed", error=str(e))

def get_db_connection(db_path: Path = None) -> sqlite3.Connection:
    """
    Returns a configured SQLite connection with WAL mode and GeoPackage metadata.
    """
    path = db_path or get_db_path()
    
    conn = sqlite3.connect(str(path))
    
    # helper for WAL mode
    try:
        # Enable Write-Ahead Logging
        conn.execute("PRAGMA journal_mode=WAL;")
        
        # Normal sync is safe enough for most desktop apps and faster than FULL
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        # Increase cache size (default is usually 2000 pages)
        conn.execute("PRAGMA cache_size=-64000;") # ~64MB
        
        # Enforce foreign keys (good practice)
        conn.execute("PRAGMA foreign_keys=ON;")
        
        # Initialize GPKG metadata
        init_geopackage(conn)
        
    except Exception as e:
        logger.error("db_config_failed", error=str(e))
        
    return conn
