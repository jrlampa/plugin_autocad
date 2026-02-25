import sqlite3
from pathlib import Path
from backend.shared.config import config
from backend.shared.logger import get_logger

logger = get_logger(__name__)

# Single source of truth for DB Path
DB_PATH = Path(config.localappdata) / "sisRUA" / "projects.db"

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

def init_schema(conn: sqlite3.Connection):
    """
    Creates the core application tables if they do not already exist.

    Called on every connection so that fresh deployments (Docker, CI, dev) work
    without manually running seed.py.  All statements are idempotent
    (CREATE TABLE IF NOT EXISTS / CREATE INDEX IF NOT EXISTS).
    """
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS Projects (
                project_id   TEXT PRIMARY KEY,
                project_name TEXT NOT NULL,
                creation_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                crs_out      TEXT,
                version      INTEGER DEFAULT 1
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS CadFeatures (
                feature_id   INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id   TEXT NOT NULL,
                feature_type TEXT NOT NULL,
                layer        TEXT,
                name         TEXT,
                highway      TEXT,
                width_m      REAL,
                color        TEXT,
                elevation    REAL,
                slope        REAL,
                original_geojson_properties TEXT,
                coords_xy    TEXT,
                insertion_point_xy TEXT,
                block_name   TEXT,
                rotation     REAL DEFAULT 0.0,
                scale        REAL DEFAULT 1.0,
                FOREIGN KEY (project_id) REFERENCES Projects(project_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS AuditLog (
                audit_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type  TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id   TEXT,
                user_id     TEXT,
                timestamp   REAL NOT NULL,
                data_json   TEXT,
                signature   TEXT NOT NULL,
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes (idempotent)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cadfeatures_project_id ON CadFeatures(project_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_cadfeatures_feature_type ON CadFeatures(feature_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_projects_creation_date_desc ON Projects(creation_date DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_auditlog_entity ON AuditLog(entity_type, entity_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_auditlog_timestamp ON AuditLog(timestamp DESC)"
        )

        conn.commit()
    except Exception as e:
        logger.error("schema_init_failed", error=str(e))


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

        # Initialize application schema (idempotent)
        init_schema(conn)
        
    except Exception as e:
        logger.error("db_config_failed", error=str(e))
        
    return conn
