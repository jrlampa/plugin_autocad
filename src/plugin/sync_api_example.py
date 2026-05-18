import sqlite3
import os
from fastapi import APIRouter, HTTPException, Depends, Header, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

try:
    import geopandas as gpd
    from shapely.geometry import Point, LineString, Polygon, shape
    HAS_GEOPANDAS = True
except ImportError:
    HAS_GEOPANDAS = False
    print("WARNING: geopandas/shapely not installed. Sync to GDF will fail.")


router = APIRouter(prefix="/api/v1/sync", tags=["Synchronization"])

# ==========================================
# DTOs (Data Transfer Objects)
# Estes modelos refletem exatamente o que o C# (CadFeatureDto) envia.
# ==========================================
class CadFeatureSyncDto(BaseModel):
    feature_id: str = Field(..., description="UUID único gerado no C#")
    project_id: str
    feature_type: str = Field(..., description="Equivalente ao Enum CadFeatureDtoType")
    layer: Optional[str] = None
    name: Optional[str] = None
    highway: Optional[str] = None
    width_m: Optional[float] = None
    coords_xy: Optional[List[List[float]]] = Field(None, description="Coordenadas [[x1,y1], [x2,y2]]")
    insertion_point_xy: Optional[List[float]] = None
    block_name: Optional[str] = None
    block_filepath: Optional[str] = None
    rotation: Optional[float] = None
    scale: Optional[float] = None
    color: Optional[str] = None
    elevation: Optional[float] = None
    slope: Optional[float] = None
    original_geojson_properties: Optional[Dict[str, Any]] = None
    revision_version: int = Field(1, description="Versão para bloqueio otimista (Optimistic Locking)")
    
class ProjectSyncPayload(BaseModel):
    project_id: str
    project_name: str
    crs_out: Optional[str] = Field(None, description="Sistema de coordenadas (Ex: EPSG:31983)")
    features: List[CadFeatureSyncDto]

# ==========================================
# PERSISTÊNCIA (SQLite Temporário/Local)
# ==========================================
DB_PATH = os.path.join(os.path.dirname(__file__), "cloud_sync_state.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feature_versions (
                feature_id TEXT PRIMARY KEY,
                project_id TEXT,
                revision_version INTEGER NOT NULL
            )
        """)
        # Mock de conflito para demonstração
        conn.execute("INSERT OR IGNORE INTO feature_versions (feature_id, project_id, revision_version) VALUES ('uuid-1111', 'mock-proj', 2)")
        conn.commit()

init_db()

# ==========================================
# UTILS
# ==========================================
def payload_to_geodataframe(payload: ProjectSyncPayload) -> 'gpd.GeoDataFrame':
    """
    Converte o DTO de Sincronização em um GeoDataFrame do GeoPandas.
    """
    if not HAS_GEOPANDAS:
        raise RuntimeError("GeoPandas is not available in this environment.")
        
    features_data = []
    geometries = []
    
    for feat in payload.features:
        # Extrai os atributos (excluindo coordenadas brutas para não poluir o GDF)
        row_data = feat.model_dump(exclude={'coords_xy', 'insertion_point_xy', 'original_geojson_properties'})
        
        # Reconstrói a propriedade original se existir (flattening basic properties for GDF)
        if feat.original_geojson_properties:
             for k, v in feat.original_geojson_properties.items():
                 if k not in row_data:
                     row_data[f"osm_{k}"] = v
                     
        features_data.append(row_data)
        
        # Constrói a geometria Shapely apropriada
        geom = None
        if feat.feature_type.lower() == 'point' or feat.feature_type.lower() == 'block':
             if feat.insertion_point_xy and len(feat.insertion_point_xy) >= 2:
                 geom = Point(feat.insertion_point_xy[0], feat.insertion_point_xy[1])
        elif feat.feature_type.lower() == 'polyline':
             if feat.coords_xy and len(feat.coords_xy) >= 2:
                 geom = LineString(feat.coords_xy)
                 
        geometries.append(geom)
        
    # Define o CRS padrão (EPSG:4326 se não for fornecido, assumindo que dados de CAD já vêm projetados, mas precisam de CRS)
    crs = payload.crs_out if payload.crs_out else "EPSG:4326" 
    return gpd.GeoDataFrame(features_data, geometry=geometries, crs=crs)

def get_server_version(feature_id: str) -> int:
    with get_db_connection() as conn:
        row = conn.execute("SELECT revision_version FROM feature_versions WHERE feature_id = ?", (feature_id,)).fetchone()
        if row:
            return row["revision_version"]
    return 0

def update_server_version(feature_id: str, project_id: str, new_version: int):
    with get_db_connection() as conn:
        conn.execute("""
            INSERT INTO feature_versions (feature_id, project_id, revision_version)
            VALUES (?, ?, ?)
            ON CONFLICT(feature_id) DO UPDATE SET revision_version = ?
        """, (feature_id, project_id, new_version, new_version))
        conn.commit()

# ==========================================
# ROTAS
# ==========================================
@router.get("/{project_id}", response_model=ProjectSyncPayload)
async def get_project_data(project_id: str, x_request_id: str = Header(None)):
    """
    PULL: Retorna o estado atual do projeto na nuvem.
    O plugin C# usa esta rota para baixar atualizações e lidar com conflitos locais.
    """
    # Simulando uma feature devolvida pela nuvem (já tratada na layer de conflito visual para o CAD)
    cloud_feature = CadFeatureSyncDto(
        feature_id="uuid-1111",
        project_id=project_id,
        feature_type="Polyline",
        layer="SISRUA_CONFLITO_REVISAO",
        coords_xy=[[0.0, 0.0], [20.0, 0.0], [20.0, 20.0]],
        revision_version=2
    )
    
    return ProjectSyncPayload(
        project_id=project_id,
        project_name=f"Projeto {project_id} (Nuvem)",
        crs_out="EPSG:31983",
        features=[cloud_feature]
    )

@router.post("/")
async def sync_project_data(
    payload: ProjectSyncPayload, 
    x_request_id: str = Header(None)
):
    """
    Recebe o Delta (apenas dados não sincronizados) do AutoCAD e faz o merge no banco mestre (Nuvem).
    """
    # TODO: 1. Autenticar usuário (SISRUA_AUTH_TOKEN)
    
    if not payload.features:
        return {"status": "success", "message": "No new features to sync.", "project_id": payload.project_id}
        
    # --- ESTRATÉGIA DE BLOQUEIO OTIMISTA (OPTIMISTIC LOCKING) ---
    conflicts = []
    for feat in payload.features:
        server_version = get_server_version(feat.feature_id)
        
        # Se a feature vier na layer de conflito, o usuário do CAD revisou e decidiu forçar esta geometria
        is_resolved_conflict = (feat.layer == "SISRUA_CONFLITO_REVISAO")
        
        if server_version > 0 and feat.revision_version < server_version and not is_resolved_conflict:
            conflicts.append({
                "feature_id": feat.feature_id,
                "client_version": feat.revision_version,
                "server_version": server_version
            })
            
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"message": "Conflito de Versão. Faça um PULL (SISRUA_SYNC_PULL) antes de enviar.", "conflicts": conflicts}
        )

    try:
        # Converte para GeoDataFrame
        gdf = payload_to_geodataframe(payload)
        
        # Exemplo de como usar o GDF (apenas printa as dimensões no log do backend)
        print(f"Syncing GDF for {payload.project_name} with shape {gdf.shape} and CRS {gdf.crs}")
        
        # TODO: 2. Inserir gdf em um PostGIS / SQLite Master usando gdf.to_postgis() ou gdf.to_file()
        # TODO: 3. Resolver conflitos
        
        # Atualiza as versões no banco de dados persistente após sucesso
        for feat in payload.features:
            # Avança a versão baseando-se na atual do servidor + 1, garantindo o versionamento contínuo
            new_version = get_server_version(feat.feature_id) + 1 if get_server_version(feat.feature_id) > 0 else feat.revision_version
            update_server_version(feat.feature_id, feat.project_id, new_version)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process geometry: {str(e)}")

    return {"status": "success", "message": f"{len(payload.features)} features received.", "project_id": payload.project_id}