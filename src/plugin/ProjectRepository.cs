using System;
using System.Collections.Generic;
using System.Data.SQLite;
using System.IO;
using System.Linq;
using System.Text.Json;
namespace sisRUA
{
    public class ProjectRepository
    {
        private static string _databasePath;
        private static readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions { WriteIndented = false };

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
                            crs_out TEXT
                        );";
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
                                INSERT INTO Projects (project_id, project_name, creation_date, crs_out)
                                VALUES (@projectId, @projectName, @creationDate, @crsOut)
                                ON CONFLICT(project_id) DO UPDATE SET
                                    project_name = @projectName,
                                    creation_date = @creationDate,
                                    crs_out = @crsOut;
                            ";
                            command.Parameters.AddWithValue("@projectId", projectId);
                            command.Parameters.AddWithValue("@projectName", projectName);
                            command.Parameters.AddWithValue("@creationDate", DateTime.UtcNow.ToString("o"));
                            command.Parameters.AddWithValue("@crsOut", crsOut);
                            command.ExecuteNonQuery();
                            SisRuaLog.Info($"DEBUG: Project '{projectId}' saved/updated.");
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
                                        rotation, scale, original_geojson_properties_json
                                    ) VALUES (
                                        @featureId, @projectId, @featureType, @layer, @name, @highway, @widthM,
                                        @coordsXyJson, @insertionPointXyJson, @blockName, @blockFilepath,
                                        @rotation, @scale, @originalGeoJsonPropertiesJson
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
                                command.Parameters.AddWithValue("@originalGeoJsonPropertiesJson", (object)DBNull.Value); // Placeholder for now

                                command.ExecuteNonQuery();
                            }
                        }
                        transaction.Commit();
                        SisRuaLog.Info($"INFO: Project '{projectId}' saved successfully with {features.Count()} features.");
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

                            features.Add(feature);
                        }
                    }
                }
            }
            SisRuaLog.Info($"INFO: Project '{projectId}' loaded successfully with {features.Count} features.");
            return (projectName, crsOut, features);
        }

        // Placeholder for ListProjects
        public List<(string projectId, string projectName, string creationDate)> ListProjects()
        {
            SisRuaLog.Info("INFO: Listing all projects.");
            List<(string projectId, string projectName, string creationDate)> projects = new List<(string projectId, string projectName, string creationDate)>();
            using (var connection = GetConnection())
            {
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT project_id, project_name, creation_date FROM Projects ORDER BY creation_date DESC;";
                    using (var reader = command.ExecuteReader())
                    {
                        while (reader.Read())
                        {
                            projects.Add((
                                reader.GetString(0), // project_id
                                reader.GetString(1), // project_name
                                reader.GetString(2)  // creation_date
                            ));
                        }
                    }
                }
            }
            SisRuaLog.Info($"INFO: Found {projects.Count} projects.");
            return projects;
        }
    }
}
