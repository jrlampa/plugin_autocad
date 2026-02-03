using System;
using System.Collections.Generic;
using System.Data.SQLite;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
namespace sisRUA
{
    public class ProjectRepository
    {
        private static string _databasePath;
        private static readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions { WriteIndented = false };
        private static readonly HttpClient _httpClient = new HttpClient { Timeout = TimeSpan.FromSeconds(2) };

        public ProjectRepository()
        {
            InitializeDatabasePath();
            CreateTablesIfNotExist();
        }

        private void InitializeDatabasePath()
        {
            if (!string.IsNullOrEmpty(_databasePath)) return;

            string localSisRuaDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "sisRUA");
            _databasePath = Path.Combine(localSisRuaDir, "projects.db");
            SisRuaLog.Info($"SQLite Database path: {_databasePath}");
        }

        private SQLiteConnection GetConnection()
        {
            var connection = new SQLiteConnection($"Data Source={_databasePath};Version=3;");
            connection.Open();
            return connection;
        }

        private void CreateTablesIfNotExist()
        {
            using (var connection = GetConnection())
            {
                using (var command = connection.CreateCommand())
                {
                    // Tabela Projects
                    command.CommandText = @"
                        CREATE TABLE IF NOT EXISTS Projects (
                            project_id TEXT PRIMARY KEY NOT NULL,
                            project_name TEXT NOT NULL,
                            creation_date TEXT NOT NULL,
                            crs_out TEXT,
                            total_mileage_km REAL DEFAULT 0
                        );
                        
                        -- GEOPACKAGE COMPATIBILITY (Enterprise-Anexável)
                        CREATE TABLE IF NOT EXISTS gpkg_spatial_ref_sys (
                            srs_name TEXT NOT NULL,
                            srs_id INTEGER PRIMARY KEY NOT NULL,
                            organization TEXT NOT NULL,
                            organization_coordsys_id INTEGER NOT NULL,
                            definition TEXT NOT NULL,
                            description TEXT
                        );

                        CREATE TABLE IF NOT EXISTS gpkg_contents (
                            table_name TEXT NOT NULL PRIMARY KEY,
                            data_type TEXT NOT NULL,
                            identifier TEXT UNIQUE,
                            description TEXT DEFAULT '',
                            last_change DATETIME NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                            min_x DOUBLE,
                            min_y DOUBLE,
                            max_x DOUBLE,
                            max_y DOUBLE,
                            srs_id INTEGER,
                            CONSTRAINT fk_gc_r_srs_id FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
                        );

                        CREATE TABLE IF NOT EXISTS gpkg_geometry_columns (
                            table_name TEXT NOT NULL,
                            column_name TEXT NOT NULL,
                            geometry_type_name TEXT NOT NULL,
                            srs_id INTEGER NOT NULL,
                            z TINYINT NOT NULL,
                            m TINYINT NOT NULL,
                            CONSTRAINT pk_ggc PRIMARY KEY (table_name, column_name),
                            CONSTRAINT fk_ggc_srs FOREIGN KEY (srs_id) REFERENCES gpkg_spatial_ref_sys(srs_id)
                        );
                    ";
                    command.ExecuteNonQuery();
                    SisRuaLog.Info("DEBUG: 'Projects' table ensured.");

                    // Tabela CadFeatures
                    command.CommandText = @"
                        CREATE TABLE IF NOT EXISTS CadFeatures (
                            feature_id TEXT PRIMARY KEY NOT NULL,
                            project_id TEXT NOT NULL,
                            feature_type TEXT NOT NULL,
                            layer TEXT,
                            name TEXT,
                            highway TEXT,
                            width_m REAL,
                            coords_xy_json TEXT,
                            insertion_point_xy_json TEXT,
                            block_name TEXT,
                            block_filepath TEXT,
                            rotation REAL,
                            scale REAL,
                            color TEXT,
                            elevation REAL,
                            slope REAL,
                            original_geojson_properties_json TEXT,
                            FOREIGN KEY (project_id) REFERENCES Projects (project_id)
                        );";
                    command.ExecuteNonQuery();
                    SisRuaLog.Info("DEBUG: 'CadFeatures' table ensured.");
                }
            }
        }

        // Placeholder for SaveProject
        public void SaveProject(string projectId, string projectName, string crsOut, IEnumerable<CadFeature> features)
        {
            SisRuaLog.Info($"INFO: Attempting to save project {projectId} - {projectName}.");
            using (var connection = GetConnection())
            {
                using (var transaction = connection.BeginTransaction())
                {
                    try
                    {
                        // Insert/Update Project
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = @"
                                INSERT INTO Projects (project_id, project_name, creation_date, crs_out, total_mileage_km)
                                VALUES (@projectId, @projectName, @creationDate, @crsOut, @mileage)
                                ON CONFLICT(project_id) DO UPDATE SET
                                    project_name = @projectName,
                                    creation_date = @creationDate,
                                    crs_out = @crsOut,
                                    total_mileage_km = @mileage;
                            ";
                            command.Parameters.AddWithValue("@projectId", projectId);
                            command.Parameters.AddWithValue("@projectName", projectName);
                            command.Parameters.AddWithValue("@creationDate", DateTime.UtcNow.ToString("o"));
                            command.Parameters.AddWithValue("@crsOut", crsOut);
                            command.Parameters.AddWithValue("@mileage", GeometryUtils.CalculateTotalMileageKm(features));
                            command.ExecuteNonQuery();
                            SisRuaLog.Info($"DEBUG: Project '{projectId}' saved/updated with mileage.");

                            // GEOPACKAGE POPULATION (Audit-Readiness)
                            try {
                                int srsId = 4326; 
                                if (!string.IsNullOrEmpty(crsOut) && crsOut.Contains(":")) {
                                    int.TryParse(crsOut.Split(':')[1], out srsId);
                                }

                                command.CommandText = @"
                                    INSERT OR REPLACE INTO gpkg_spatial_ref_sys (srs_name, srs_id, organization, organization_coordsys_id, definition)
                                    VALUES (@srsName, @srsId, 'EPSG', @srsId, 'PROJCS[]');
                                    
                                    INSERT OR REPLACE INTO gpkg_contents (table_name, data_type, identifier, description, srs_id)
                                    VALUES ('CadFeatures', 'features', @projId, @projName, @srsId);
                                    
                                    INSERT OR REPLACE INTO gpkg_geometry_columns (table_name, column_name, geometry_type_name, srs_id, z, m)
                                    VALUES ('CadFeatures', 'geometry_blob', 'GEOMETRY', @srsId, 0, 0);
                                ";
                                command.Parameters.Clear();
                                command.Parameters.AddWithValue("@srsName", "SIRGAS 2000 / UTM");
                                command.Parameters.AddWithValue("@srsId", srsId);
                                command.Parameters.AddWithValue("@projId", projectId);
                                command.Parameters.AddWithValue("@projName", projectName);
                                command.ExecuteNonQuery();
                            } catch (Exception ex) {
                                SisRuaLog.Error($"GEO_ERR: Failed to populate GPKG metadata: {ex.Message}");
                            }
                        }

                        // Delete existing features for this project before re-inserting
                        using (var command = connection.CreateCommand())
                        {
                            command.CommandText = "DELETE FROM CadFeatures WHERE project_id = @projectId;";
                            command.Parameters.AddWithValue("@projectId", projectId);
                            command.ExecuteNonQuery();
                            SisRuaLog.Info($"DEBUG: Existing features for project '{projectId}' cleared.");
                        }

                        // Insert CadFeatures
                        foreach (var feature in features)
                        {
                            using (var command = connection.CreateCommand())
                            {
                                command.CommandText = @"
                                    INSERT INTO CadFeatures (
                                        feature_id, project_id, feature_type, layer, name, highway, width_m,
                                        coords_xy_json, insertion_point_xy_json, block_name, block_filepath,
                                        rotation, scale, color, elevation, slope, original_geojson_properties_json
                                    ) VALUES (
                                        @featureId, @projectId, @featureType, @layer, @name, @highway, @widthM,
                                        @coordsXyJson, @insertionPointXyJson, @blockName, @blockFilepath,
                                        @rotation, @scale, @color, @elevation, @slope, @originalGeoJsonPropertiesJson
                                    );";
                                command.Parameters.AddWithValue("@featureId", Guid.NewGuid().ToString());
                                command.Parameters.AddWithValue("@projectId", projectId);
                                command.Parameters.AddWithValue("@featureType", feature.FeatureType.ToString());
                                command.Parameters.AddWithValue("@layer", feature.Layer ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@name", feature.Name ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@highway", feature.Highway ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@widthM", feature.WidthMeters ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@coordsXyJson", feature.CoordsXy != null ? JsonSerializer.Serialize(feature.CoordsXy, _jsonOptions) : (object)DBNull.Value);
                                command.Parameters.AddWithValue("@insertionPointXyJson", feature.InsertionPointXy != null ? JsonSerializer.Serialize(feature.InsertionPointXy, _jsonOptions) : (object)DBNull.Value);
                                command.Parameters.AddWithValue("@blockName", feature.BlockName ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@blockFilepath", feature.BlockFilePath ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@rotation", feature.Rotation ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@scale", feature.Scale ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@color", feature.Color ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@elevation", feature.Elevation ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@slope", feature.Slope ?? (object)DBNull.Value);
                                command.Parameters.AddWithValue("@originalGeoJsonPropertiesJson", feature.OriginalGeoJsonProperties != null ? JsonSerializer.Serialize(feature.OriginalGeoJsonProperties, _jsonOptions) : (object)DBNull.Value);

                                command.ExecuteNonQuery();
                            }
                        }
                        transaction.Commit();
                        SisRuaLog.Info($"INFO: Project '{projectId}' saved successfully with {features.Count()} features.");
                        
                        // Notify backend (fire-and-forget)
                        double mileage = GeometryUtils.CalculateTotalMileageKm(features);
                        _ = NotifyBackend("project_saved", new { 
                            project_id = projectId, 
                            project_name = projectName, 
                            feature_count = features.Count(),
                            mileage_km = mileage
                        });

                        // Cryptographic Audit Log (V2) - Enhanced for Valuation
                        _ = LogAuditAsync("UPDATE", "Project", projectId, new
                        {
                            project_name = projectName,
                            crs_out = crsOut,
                            feature_count = features.Count(),
                            mileage_km = mileage,
                            compliance_level = "ISO_27001_READY",
                            action = "save_project"
                        });
                    }
                    catch (System.Exception ex)
                    {
                        transaction.Rollback();
                        SisRuaLog.Info($"ERROR: Failed to save project '{projectId}': {ex.Message}");
                        throw;
                    }
                }
            }
        }

        // Placeholder for LoadProject
        public (string projectName, string crsOut, List<CadFeature> features) LoadProject(string projectId)
        {
            SisRuaLog.Info($"INFO: Attempting to load project '{projectId}'.");
            string projectName = null;
            string crsOut = null;
            List<CadFeature> features = new List<CadFeature>();

            using (var connection = GetConnection())
            {
                // Load Project details
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT project_name, crs_out FROM Projects WHERE project_id = @projectId;";
                    command.Parameters.AddWithValue("@projectId", projectId);
                    using (var reader = command.ExecuteReader())
                    {
                        if (reader.Read())
                        {
                            projectName = reader.GetString(0);
                            crsOut = reader.IsDBNull(1) ? null : reader.GetString(1);
                        }
                        else
                        {
                            SisRuaLog.Info($"WARN: Project '{projectId}' not found.");
                            return (null, null, null);
                        }
                    }
                }

                // Load CadFeatures
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT * FROM CadFeatures WHERE project_id = @projectId;";
                    command.Parameters.AddWithValue("@projectId", projectId);
                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            CadFeature feature = new CadFeature();
                            feature.FeatureType = (CadFeatureType)Enum.Parse(typeof(CadFeatureType), reader.GetString(reader.GetOrdinal("feature_type")));
                            feature.Layer = reader.IsDBNull(reader.GetOrdinal("layer")) ? null : reader.GetString(reader.GetOrdinal("layer"));
                            feature.Name = reader.IsDBNull(reader.GetOrdinal("name")) ? null : reader.GetString(reader.GetOrdinal("name"));
                            feature.Highway = reader.IsDBNull(reader.GetOrdinal("highway")) ? null : reader.GetString(reader.GetOrdinal("highway"));
                            feature.WidthMeters = reader.IsDBNull(reader.GetOrdinal("width_m")) ? null : (double?)reader.GetDouble(reader.GetOrdinal("width_m"));

                            string coordsXyJson = reader.IsDBNull(reader.GetOrdinal("coords_xy_json")) ? null : reader.GetString(reader.GetOrdinal("coords_xy_json"));
                            if (coordsXyJson != null) feature.CoordsXy = JsonSerializer.Deserialize<List<List<double>>>(coordsXyJson);

                            string insertionPointXyJson = reader.IsDBNull(reader.GetOrdinal("insertion_point_xy_json")) ? null : reader.GetString(reader.GetOrdinal("insertion_point_xy_json"));
                            if (insertionPointXyJson != null) feature.InsertionPointXy = JsonSerializer.Deserialize<List<double>>(insertionPointXyJson);
                            
                            feature.BlockName = reader.IsDBNull(reader.GetOrdinal("block_name")) ? null : reader.GetString(reader.GetOrdinal("block_name"));
                            feature.BlockFilePath = reader.IsDBNull(reader.GetOrdinal("block_filepath")) ? null : reader.GetString(reader.GetOrdinal("block_filepath"));
                            feature.Rotation = reader.IsDBNull(reader.GetOrdinal("rotation")) ? null : (double?)reader.GetDouble(reader.GetOrdinal("rotation"));
                            feature.Scale = reader.IsDBNull(reader.GetOrdinal("scale")) ? null : (double?)reader.GetDouble(reader.GetOrdinal("scale"));
                            feature.Color = reader.IsDBNull(reader.GetOrdinal("color")) ? null : reader.GetString(reader.GetOrdinal("color"));
                            feature.Elevation = reader.IsDBNull(reader.GetOrdinal("elevation")) ? null : (double?)reader.GetDouble(reader.GetOrdinal("elevation"));
                            feature.Slope = reader.IsDBNull(reader.GetOrdinal("slope")) ? null : (double?)reader.GetDouble(reader.GetOrdinal("slope"));

                            string propertiesJson = reader.IsDBNull(reader.GetOrdinal("original_geojson_properties_json")) ? null : reader.GetString(reader.GetOrdinal("original_geojson_properties_json"));
                            if (propertiesJson != null) feature.OriginalGeoJsonProperties = JsonSerializer.Deserialize<Dictionary<string, object>>(propertiesJson);

                            features.Add(feature);
                        }
                    }
                }
            }
            SisRuaLog.Info($"INFO: Project '{projectId}' loaded successfully with {features.Count} features.");
            
            // Notify backend (fire-and-forget)
            _ = NotifyBackend("project_loaded", new { project_id = projectId, project_name = projectName, feature_count = features.Count });

            // Cryptographic Audit Log (V2)
            _ = LogAuditAsync("READ", "Project", projectId, new
            {
                project_name = projectName,
                feature_count = features.Count,
                action = "load_project"
            });

            return (projectName, crsOut, features);
        }

        // Placeholder for ListProjects
        public List<(string projectId, string projectName, string creationDate, string totalMileageKm)> ListProjects()
        {
            SisRuaLog.Info("INFO: Listing all projects.");
            List<(string projectId, string projectName, string creationDate, string totalMileageKm)> projects = new List<(string projectId, string projectName, string creationDate, string totalMileageKm)>();
            using (var connection = GetConnection())
            {
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT project_id, project_name, creation_date, total_mileage_km FROM Projects ORDER BY creation_date DESC;";
                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            projects.Add((
                                reader.GetString(0), // project_id
                                reader.GetString(1), // project_name
                                reader.GetString(2), // creation_date
                                reader.GetDouble(3).ToString("F2") + " km" // mileage as string for UI
                            ));
                        }
                    }
                }
            }
            SisRuaLog.Info($"INFO: Found {projects.Count} projects.");
            return projects;
        }

        private async Task NotifyBackend(string eventType, object payload)
        {
            if (string.IsNullOrEmpty(SisRuaPlugin.BackendBaseUrl)) return;

            try
            {
                var eventData = new
                {
                    event_type = eventType,
                    payload = payload
                };

                string json = JsonSerializer.Serialize(eventData, _jsonOptions);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                if (!string.IsNullOrEmpty(SisRuaPlugin.BackendAuthToken))
                {
                    content.Headers.Add(SisRuaPlugin.BackendAuthHeaderName, SisRuaPlugin.BackendAuthToken);
                }
                content.Headers.Add("X-Request-ID", Guid.NewGuid().ToString());

                await _httpClient.PostAsync($"{SisRuaPlugin.BackendBaseUrl}/api/v1/events/emit", content);
            }
            catch (Exception ex)
            {
                SisRuaLog.Info($"DEBUG: Failed to notify backend for event {eventType}: {ex.Message}");
            }
        }

        private async Task LogAuditAsync(string eventType, string entityType, string entityId, object data)
        {
            if (string.IsNullOrEmpty(SisRuaPlugin.BackendBaseUrl)) return;

            try
            {
                var auditData = new
                {
                    event_type = eventType,
                    entity_type = entityType,
                    entity_id = entityId,
                    user_id = Environment.UserName, // Default to system user for now
                    data = data
                };

                string json = JsonSerializer.Serialize(auditData, _jsonOptions);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                if (!string.IsNullOrEmpty(SisRuaPlugin.BackendAuthToken))
                {
                    content.Headers.Add(SisRuaPlugin.BackendAuthHeaderName, SisRuaPlugin.BackendAuthToken);
                }
                content.Headers.Add("X-Request-ID", Guid.NewGuid().ToString());

                // Call the new Audit API (V2)
                var response = await _httpClient.PostAsync($"{SisRuaPlugin.BackendBaseUrl}/api/audit", content);
                
                if (!response.IsSuccessStatusCode)
                {
                    string error = await response.Content.ReadAsStringAsync();
                    SisRuaLog.Info($"DEBUG: Audit logging failed ({response.StatusCode}): {error}");
                }
            }
            catch (Exception ex)
            {
                SisRuaLog.Info($"DEBUG: Failed to log audit event {eventType} for {entityType}:{entityId}: {ex.Message}");
            }
        }
    }
}
