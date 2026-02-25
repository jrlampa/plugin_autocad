import json
import sqlite3
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from backend.shared.logger import get_logger

logger = get_logger(__name__)


class ExportService:
    def __init__(self, db_path: Path):
        self.db_path = db_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _fetch_cad_rows(self, conn: sqlite3.Connection, project_id: str) -> list:
        return conn.execute(
            """
            SELECT feature_type, layer, name, highway, width_m, color,
                   elevation, slope, original_geojson_properties, coords_xy,
                   insertion_point_xy, block_name, rotation, scale
            FROM CadFeatures WHERE project_id = ?
            """,
            (project_id,),
        ).fetchall()

    def _check_project_exists(self, conn: sqlite3.Connection, project_id: str) -> bool:
        row = conn.execute(
            "SELECT 1 FROM Projects WHERE project_id = ?", (project_id,)
        ).fetchone()
        return row is not None

    # ------------------------------------------------------------------
    # GeoJSON export
    # ------------------------------------------------------------------

    def export_project_to_geojson(self, project_id: str) -> Path:
        """Exports a project as a standard GeoJSON FeatureCollection."""
        logger.info("exporting_geojson", project_id=project_id)
        conn = sqlite3.connect(self.db_path)
        try:
            if not self._check_project_exists(conn, project_id):
                from backend.application.projects import NotFoundError
                raise NotFoundError(f"Projeto '{project_id}' não encontrado.")

            rows = self._fetch_cad_rows(conn, project_id)
            features = []
            for row in rows:
                (f_type, layer, name, highway, width, color, elev, slope,
                 props_json, coords_json, _ip, _bn, _rot, _sc) = row

                props = json.loads(props_json) if props_json else {}
                coords = json.loads(coords_json) if coords_json else []

                props.update({
                    "sisrua:feature_type": f_type,
                    "sisrua:layer": layer,
                    "sisrua:name": name,
                    "sisrua:highway": highway,
                    "sisrua:width_m": width,
                    "sisrua:color": color,
                    "sisrua:elevation": elev,
                    "sisrua:slope": slope,
                })

                features.append({
                    "type": "Feature",
                    "properties": props,
                    "geometry": {
                        "type": "LineString" if f_type == "Polyline" else "Point",
                        "coordinates": coords,
                    },
                })

            geojson = {
                "type": "FeatureCollection",
                "features": features,
                "metadata": {
                    "project_id": project_id,
                    "exported_at": datetime.now(timezone.utc).isoformat(),
                },
            }

            temp_dir = Path(tempfile.mkdtemp())
            export_file = temp_dir / f"sisrua_{project_id}.geojson"
            with open(export_file, "w", encoding="utf-8") as f:
                json.dump(geojson, f, indent=2)

            return export_file
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # GeoPackage export
    # ------------------------------------------------------------------

    def export_project_to_geopackage(self, project_id: str) -> Path:
        """
        Generates a GPKG package by copying the DB and purging other projects.
        """
        logger.info("exporting_geopackage", project_id=project_id)

        temp_dir = Path(tempfile.mkdtemp())
        export_file = temp_dir / f"sisrua_{project_id}.gpkg"

        shutil.copy2(self.db_path, export_file)

        conn = sqlite3.connect(export_file)
        try:
            if not self._check_project_exists(conn, project_id):
                from backend.application.projects import NotFoundError
                raise NotFoundError(f"Projeto '{project_id}' não encontrado.")

            conn.execute("DELETE FROM CadFeatures WHERE project_id != ?", (project_id,))
            conn.execute("DELETE FROM Projects WHERE project_id != ?", (project_id,))

            project_info = conn.execute(
                "SELECT project_name, crs_out FROM Projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            project_name, crs_out = project_info

            srs_id = 4326
            if crs_out and "EPSG:" in crs_out:
                try:
                    srs_id = int(crs_out.split(":")[1])
                except ValueError:
                    pass

            # Register GPKG tables only if they exist (SQLite copy may lack them)
            tables = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()}

            if "gpkg_contents" in tables:
                conn.execute(
                    """INSERT OR REPLACE INTO gpkg_contents
                       (table_name, data_type, identifier, description, srs_id)
                       VALUES (?, ?, ?, ?, ?)""",
                    ("CadFeatures", "features", project_id,
                     f"sisRUA Project: {project_name}", srs_id),
                )

            if "gpkg_geometry_columns" in tables:
                conn.execute(
                    """INSERT OR REPLACE INTO gpkg_geometry_columns
                       (table_name, column_name, geometry_type_name, srs_id, z, m)
                       VALUES (?, ?, ?, ?, 1, 0)""",
                    ("CadFeatures", "coords_xy", "GEOMETRY", srs_id),
                )

            conn.commit()
            conn.execute("VACUUM")
        finally:
            conn.close()

        return export_file

    # ------------------------------------------------------------------
    # DXF export (ABNT NBR 14166 / 13133 — 2.5D)
    # ------------------------------------------------------------------

    def export_project_to_dxf(
        self,
        project_id: str,
        escala: int = 1_000,
        prodist_metadata=None,
        include_prodist_buffers: bool = False,
    ) -> Path:
        """
        Exporta um projeto como arquivo DXF R2010 com metadados ABNT ou PRODIST.

        Princípio 2.5D: elevação armazenada como XDATA, não como coordenada Z.
        Conformidade: ABNT NBR 14166:1998 e NBR 13133:2021 (padrão).
        Quando `prodist_metadata` é fornecido, usa ANEEL/PRODIST (substitui ABNT).

        Args:
            project_id:             Identificador do projeto no banco de dados.
            escala:                 Escala cartográfica padrão ABNT (padrão: 1:1.000).
            prodist_metadata:       Metadados PRODIST. Quando presente, substitui ABNT
                                    no cabeçalho DXF.
            include_prodist_buffers: Quando True e `prodist_metadata` não é None,
                                    gera faixas de segurança NR-10:2016 nas camadas
                                    SISRUA_ANEEL_BUFFER_*.

        Returns:
            Path para o arquivo .dxf gerado em diretório temporário.
        """
        from backend.domain.dto import CadFeature
        from backend.application.dxf_export import export_features_to_dxf
        from backend.domain.abnt import build_default_metadata, nearest_abnt_escala, AbntDrawingMetadata

        logger.info("exporting_dxf", project_id=project_id, escala=escala)
        conn = sqlite3.connect(self.db_path)
        try:
            if not self._check_project_exists(conn, project_id):
                from backend.application.projects import NotFoundError
                raise NotFoundError(f"Projeto '{project_id}' não encontrado.")

            project_info = conn.execute(
                "SELECT project_name, crs_out FROM Projects WHERE project_id = ?",
                (project_id,),
            ).fetchone()
            project_name, crs_out = project_info

            # Derive EPSG from stored CRS string (e.g. "EPSG:31983")
            epsg = 31983
            if crs_out and "EPSG:" in crs_out:
                try:
                    epsg = int(crs_out.split(":")[1])
                except ValueError:
                    pass

            rows = self._fetch_cad_rows(conn, project_id)
            features: List[CadFeature] = []
            for row in rows:
                (f_type, layer, name, highway, width, color, elev, slope,
                 props_json, coords_json, ip_json, block_name, rotation, scale) = row

                coords = json.loads(coords_json) if coords_json else []
                ip = json.loads(ip_json) if ip_json else []
                props = json.loads(props_json) if props_json else {}

                features.append(
                    CadFeature(
                        feature_type=f_type or "Polyline",
                        layer=layer or "0",
                        name=name,
                        highway=highway,
                        width_m=width,
                        color=color,
                        elevation=elev,
                        slope=slope,
                        coords_xy=coords if f_type == "Polyline" else [],
                        insertion_point_xy=ip if f_type == "Point" else [],
                        block_name=block_name,
                        rotation=rotation or 0.0,
                        scale=scale or 1.0,
                        original_geojson_properties=props,
                    )
                )

            temp_dir = Path(tempfile.mkdtemp())
            export_file = temp_dir / f"sisrua_{project_id}.dxf"

            if prodist_metadata is not None:
                export_features_to_dxf(
                    features,
                    output_path=export_file,
                    prodist_metadata=prodist_metadata,
                    include_prodist_buffers=include_prodist_buffers,
                    epsg=epsg,
                )
            else:
                abnt_escala = nearest_abnt_escala(escala)
                default_meta = build_default_metadata(epsg)
                metadata = AbntDrawingMetadata(
                    crs_label=default_meta.crs_label,
                    epsg=epsg,
                    escala=abnt_escala,
                    orgao=f"sisRUA — {project_name}",
                    datum=default_meta.datum,
                    projecao=default_meta.projecao,
                    unidade=default_meta.unidade,
                    zona_utm=default_meta.zona_utm,
                )
                export_features_to_dxf(
                    features,
                    output_path=export_file,
                    metadata=metadata,
                    epsg=epsg,
                )
            return export_file
        finally:
            conn.close()
