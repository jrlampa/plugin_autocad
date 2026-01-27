using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Reflection;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;

namespace sisRUA
{
    /// <summary>
    /// Contém os comandos do AutoCAD e a lógica de negócio para interagir com o desenho e o backend.
    /// </summary>
    public class SisRuaCommands
    {
        private static readonly HttpClient _httpClient = new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
        private static readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };

        /// <summary>
        /// Garante que uma definição de bloco esteja carregada no desenho.
        /// Se não existir, carrega-a do arquivo especificado.
        /// </summary>
        /// <param name="tr">Transação ativa.</param>
        /// <param name="db">Database do desenho atual.</param>
        /// <param name="blockName">Nome do bloco na BlockTable (ex: POSTE_GENERICO).</param>
        /// <param name="blockFilePath">Caminho completo para o arquivo DXF/DWG contendo a definição do bloco.</param>
        /// <returns>ObjectId da definição do bloco na BlockTable.</returns>
        private static ObjectId EnsureBlockDefinitionLoaded(Transaction tr, Database db, string blockName, string blockFilePath)
        {
            Log($"INFO: Ensuring block definition '{blockName}' from '{blockFilePath}' is loaded.");
            BlockTable bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);

            if (bt.Has(blockName))
            {
                Log($"DEBUG: Block '{blockName}' already loaded.");
                return bt[blockName];
            }

            Log($"INFO: Block '{blockName}' not found. Loading from file '{blockFilePath}'.");
            using (Database blockDb = new Database(false, true))
            {
                // Tenta ler como DWG ou DXF
                try
                {
                    blockDb.ReadDwgFile(blockFilePath, FileShare.Read, true, "");
                }
                catch (System.Exception ex)
                {
                    Log($"ERROR: Failed to read block file '{blockFilePath}' as DWG: {ex.Message}");
                    try
                    {
                        // Tenta ler como DXF se DWG falhar
                        blockDb.DxfIn(blockFilePath, "");
                    }
                    catch (System.Exception dxfEx)
                    {
                        Log($"ERROR: Failed to read block file '{blockFilePath}' as DXF: {dxfEx.Message}");
                        throw new System.Exception($"Não foi possível carregar a definição do bloco '{blockName}' do arquivo '{blockFilePath}'. Erro: {dxfEx.Message}", dxfEx);
                    }
                }

                ObjectIdCollection ids = new ObjectIdCollection();
                // Itera sobre a BlockTable do arquivo do bloco para encontrar a definição do bloco
                using (Transaction blockTr = blockDb.TransactionManager.StartTransaction())
                {
                    BlockTable blockFileBt = (BlockTable)blockTr.GetObject(blockDb.BlockTableId, OpenMode.ForRead);
                    foreach (ObjectId btrId in blockFileBt)
                    {
                        BlockTableRecord btr = (BlockTableRecord)blockTr.GetObject(btrId, OpenMode.ForRead);
                        // Ignora blocos anônimos e layout (model/paper space)
                        if (btr.IsAnonymous || btr.IsLayout) continue;

                        // Se o bloco no arquivo for nomeado como o que queremos (ou se for o *ModelSpace),
                        // assume que a definição está lá
                        if (string.Equals(btr.Name, blockName, StringComparison.OrdinalIgnoreCase) || btr.Name == "*Model_Space")
                        {
                            ids.Add(btrId);
                        }
                    }
                    blockTr.Commit();
                }

                if (ids.Count == 0)
                {
                    throw new System.Exception($"Não foi encontrada a definição do bloco '{blockName}' dentro do arquivo '{blockFilePath}'.");
                }

                // Adiciona a definição do bloco ao desenho atual.
                bt.UpgradeOpen();
                db.Insert(blockName, blockDb, ids[0], true);
                bt.DowngradeOpen();
                Log($"INFO: Block definition '{blockName}' loaded successfully.");
                return bt[blockName];
            }
        }
        
        /// <summary>
        /// Insere uma instância de bloco no Model Space.
        /// </summary>
        /// <param name="tr">Transação ativa.</param>
        /// <param name="db">Database do desenho atual.</param>
        /// <param name="ms">BlockTableRecord do Model Space.</param>
        /// <param name="blockName">Nome do bloco a ser inserido (deve ter a definição carregada).</param>
        /// <param name="blockFilePath">Caminho para o arquivo DXF/DWG contendo a definição do bloco (usado se precisar carregar).</param>
        /// <param name="insertionPoint">Ponto de inserção do bloco.</param>
        /// <param name="rotation">Rotação do bloco em radianos.</param>
        /// <param name="scale">Fator de escala do bloco.</param>
        /// <param name="layerName">Nome da camada onde o bloco será inserido.</param>
        private static void InsertBlock(Transaction tr, Database db, BlockTableRecord ms, string blockName, string blockFilePath, Autodesk.AutoCAD.Geometry.Point3d insertionPoint, double rotation, double scale, string layerName)
        {
            Log($"INFO: Inserting block '{blockName}' at {insertionPoint.X},{insertionPoint.Y},{insertionPoint.Z}.");
            try
            {
                // Garante que a definição do bloco está carregada
                ObjectId blockDefId = EnsureBlockDefinitionLoaded(tr, db, blockName, blockFilePath);

                BlockReference br = new BlockReference(insertionPoint, blockDefId);
                br.Rotation = rotation;
                br.ScaleFactors = new Autodesk.AutoCAD.Geometry.Scale3d(scale);
                br.Layer = layerName;
                br.Color = Color.FromColorIndex(ColorMethod.ByLayer, 256); // Sempre ByLayer

                ms.AppendEntity(br);
                tr.AddNewlyCreatedDBObject(br, true);
                Log($"DEBUG: Block instance '{blockName}' inserted successfully.");
            }
            catch (System.Exception ex)
            {
                Log($"ERROR: Failed to insert block '{blockName}' at {insertionPoint.ToString()}: {ex.Message}");
                // Não propaga o erro para não interromper o desenho de outras features
            }
        }


        private static void Log(string message)
        {
            // Use the logger from SisRuaPlugin
            if (SisRuaPlugin.Instance != null)
            {
                // Accessing internal LogToEditor method via reflection for now
                // Ideally, SisRuaPlugin should expose a public static log method
                MethodInfo logMethod = typeof(SisRuaPlugin).GetMethod("LogToEditor", BindingFlags.NonPublic | BindingFlags.Instance);
                if (logMethod != null)
                {
                    logMethod.Invoke(SisRuaPlugin.Instance, new object[] { $"[SisRuaCommands] {message}" });
                }
            }
            Debug.WriteLine($"[SisRuaCommands] {message}");
        }

        private static string GetBackendBaseUrlOrAlert(Editor ed)
        {
            string baseUrl = SisRuaPlugin.BackendBaseUrl;
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                ed?.WriteMessage("\n[sisRUA] ERRO: BackendBaseUrl não definido. O plugin inicializou corretamente?");
                Application.ShowAlertDialog("Backend do sisRUA não foi inicializado corretamente.\nFeche e reabra o AutoCAD e execute o comando SISRUA novamente.");
                Log("ERROR: BackendBaseUrl not defined.");
                return null;
            }

            // Segurança extra: aguarda health por alguns segundos antes de chamar endpoints.
            SisRuaPlugin.EnsureBackendHealthy(TimeSpan.FromSeconds(10));
            return baseUrl;
        }

        private static HttpRequestMessage CreateAuthedJsonRequest(HttpMethod method, string url, string jsonBody)
        {
            var req = new HttpRequestMessage(method, url);
            if (!string.IsNullOrWhiteSpace(SisRuaPlugin.BackendAuthToken))
            {
                req.Headers.TryAddWithoutValidation(SisRuaPlugin.BackendAuthHeaderName, SisRuaPlugin.BackendAuthToken);
            }

            if (jsonBody != null)
            {
                req.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");
            }
            return req;
        }

        private sealed class PrepareOsmRequest
        {
            [JsonPropertyName("latitude")]
            public double Latitude { get; set; }

            [JsonPropertyName("longitude")]
            public double Longitude { get; set; }

            [JsonPropertyName("radius")]
            public double Radius { get; set; }
        }

        private sealed class PrepareGeoJsonRequest
        {
            [JsonPropertyName("geojson")]
            public string GeoJson { get; set; }
        }

        private sealed class PrepareResponse
        {
            [JsonPropertyName("crs_out")]
            public string CrsOut { get; set; }

            [JsonPropertyName("features")]
            public List<CadFeature> Features { get; set; }
        }

        private sealed class PrepareJobRequest
        {
            [JsonPropertyName("kind")]
            public string Kind { get; set; } // "osm" | "geojson"

            [JsonPropertyName("latitude")]
            public double? Latitude { get; set; }

            [JsonPropertyName("longitude")]
            public double? Longitude { get; set; }

            [JsonPropertyName("radius")]
            public double? Radius { get; set; }

            [JsonPropertyName("geojson")]
            public string GeoJson { get; set; }
        }

        private sealed class JobStatusResponse
        {
            [JsonPropertyName("job_id")]
            public string JobId { get; set; }

            [JsonPropertyName("kind")]
            public string Kind { get; set; }

            [JsonPropertyName("status")]
            public string Status { get; set; } // queued|processing|completed|failed

            [JsonPropertyName("progress")]
            public double Progress { get; set; } // 0..1

            [JsonPropertyName("message")]
            public string Message { get; set; }

            [JsonPropertyName("result")]
            public JsonElement Result { get; set; }

            [JsonPropertyName("error")]
            public string Error { get; set; }
        }

        private sealed class CadFeature
        {
            [JsonPropertyName("feature_type")]
            public CadFeatureType FeatureType { get; set; } = CadFeatureType.Polyline; // Default to Polyline

            [JsonPropertyName("layer")]
            public string Layer { get; set; }

            [JsonPropertyName("name")]
            public string Name { get; set; }

            [JsonPropertyName("highway")]
            public string Highway { get; set; }

            // Largura estimada da via (metros). Se presente, podemos desenhar como polyline com largura constante.
            [JsonPropertyName("width_m")]
            public double? WidthMeters { get; set; }

            // Para feições do tipo Polyline
            [JsonPropertyName("coords_xy")]
            public List<List<double>> CoordsXy { get; set; }

            // Para feições do tipo Point (blocos)
            [JsonPropertyName("insertion_point_xy")]
            public List<double> InsertionPointXy { get; set; }

            [JsonPropertyName("block_name")]
            public string BlockName { get; set; }

            [JsonPropertyName("block_filepath")]
            public string BlockFilePath { get; set; } // Path to the DXF/DWG file for this block

            [JsonPropertyName("rotation")]
            public double? Rotation { get; set; }

            [JsonPropertyName("scale")]
            public double? Scale { get; set; }
        }

        private enum CadFeatureType
        {
            Polyline,
            Point
        }


        private sealed class LayerStyle
        {
            [JsonPropertyName("layer")]
            public string Layer { get; set; }

            [JsonPropertyName("aci")]
            public short? Aci { get; set; }
        }

        private sealed class LayersConfig
        {
            [JsonPropertyName("highway")]
            public Dictionary<string, LayerStyle> Highway { get; set; }
        }

        private static readonly Lazy<Dictionary<string, LayerStyle>> _highwayLayerMap =
            new Lazy<Dictionary<string, LayerStyle>>(LoadHighwayLayerMap, isThreadSafe: true);

        private sealed class BlockMapEntry
        {
            [JsonPropertyName("block_name")]
            public string BlockName { get; set; }
            [JsonPropertyName("block_filepath")]
            public string BlockFilePath { get; set; } // Relative path from Contents/Blocks/
            [JsonPropertyName("layer")]
            public string Layer { get; set; }
            [JsonPropertyName("scale")]
            public double? Scale { get; set; }
            [JsonPropertyName("rotation")]
            public double? Rotation { get; set; }
        }

        private sealed class BlockMapConfig
        {
            [JsonPropertyName("default_block_path")]
            public string DefaultBlockPath { get; set; } // Path from Contents/ to Blocks/
            [JsonPropertyName("mappings")]
            public Dictionary<string, BlockMapEntry> Mappings { get; set; }
        }

        private static readonly Lazy<Dictionary<string, BlockMapEntry>> _blockMapping =
            new Lazy<Dictionary<string, BlockMapEntry>>(LoadBlockMapping, isThreadSafe: true);

        private static Dictionary<string, BlockMapEntry> LoadBlockMapping()
        {
            var map = new Dictionary<string, BlockMapEntry>(StringComparer.OrdinalIgnoreCase);

            try
            {
                string asmDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                if (!string.IsNullOrWhiteSpace(asmDir))
                {
                    string cfgPath = Path.Combine(asmDir, "Resources", "blocks_mapping.json");
                    if (File.Exists(cfgPath))
                    {
                        string text = File.ReadAllText(cfgPath);
                        var cfg = JsonSerializer.Deserialize<BlockMapConfig>(text, _jsonOptions);
                        if (cfg?.Mappings != null)
                        {
                            foreach (var kv in cfg.Mappings)
                            {
                                if (string.IsNullOrWhiteSpace(kv.Key) || kv.Value == null) continue;
                                // Resolve block_filepath relative to the bundle's Blocks/ folder
                                if (!string.IsNullOrWhiteSpace(cfg.DefaultBlockPath) && !Path.IsPathRooted(kv.Value.BlockFilePath))
                                {
                                    kv.Value.BlockFilePath = Path.Combine(asmDir, cfg.DefaultBlockPath, kv.Value.BlockFilePath);
                                }
                                map[kv.Key.Trim()] = kv.Value;
                            }
                        }
                    }
                }
            }
            catch (System.Exception ex)
            {
                Log($"WARN: Error loading blocks_mapping.json: {ex.Message}");
            }

            return map;
        }

        private static Dictionary<string, LayerStyle> LoadHighwayLayerMap()
        {
            // Default (embutido)
            var map = new Dictionary<string, LayerStyle>(StringComparer.OrdinalIgnoreCase)
            {
                ["motorway"] = new LayerStyle { Layer = "SISRUA_OSM_MOTORWAY", Aci = 1 },
                ["trunk"] = new LayerStyle { Layer = "SISRUA_OSM_TRUNK", Aci = 2 },
                ["primary"] = new LayerStyle { Layer = "SISRUA_OSM_PRIMARY", Aci = 3 },
                ["secondary"] = new LayerStyle { Layer = "SISRUA_OSM_SECONDARY", Aci = 4 },
                ["tertiary"] = new LayerStyle { Layer = "SISRUA_OSM_TERTIARY", Aci = 5 },
                ["residential"] = new LayerStyle { Layer = "SISRUA_OSM_RESIDENTIAL", Aci = 7 },
                ["service"] = new LayerStyle { Layer = "SISRUA_OSM_SERVICE", Aci = 8 },
                ["unclassified"] = new LayerStyle { Layer = "SISRUA_OSM_UNCLASSIFIED", Aci = 9 },
                ["living_street"] = new LayerStyle { Layer = "SISRUA_OSM_LIVING", Aci = 30 },
                ["footway"] = new LayerStyle { Layer = "SISRUA_OSM_PEDESTRIAN", Aci = 140 },
                ["path"] = new LayerStyle { Layer = "SISRUA_OSM_PATH", Aci = 141 },
                ["cycleway"] = new LayerStyle { Layer = "SISRUA_OSM_CYCLE", Aci = 150 },
            };

            // Override por arquivo (opcional): Contents/Resources/layers.json
            try
            {
                string asmDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                if (!string.IsNullOrWhiteSpace(asmDir))
                {
                    string cfgPath = Path.Combine(asmDir, "Resources", "layers.json");
                    if (File.Exists(cfgPath))
                    {
                        string text = File.ReadAllText(cfgPath);
                        var cfg = JsonSerializer.Deserialize<LayersConfig>(text, _jsonOptions);
                        if (cfg?.Highway != null)
                        {
                            foreach (var kv in cfg.Highway)
                            {
                                if (string.IsNullOrWhiteSpace(kv.Key) || kv.Value == null) continue;
                                map[kv.Key.Trim()] = kv.Value;
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"WARN: Error loading layers.json: {ex.Message}");
            }

            return map;
        }

        private static (string layerName, short? aci) GetLayerStyleForFeature(CadFeature f)
        {
            if (f == null) return ("SISRUA_VIAS", null);

            string layerName = string.IsNullOrWhiteSpace(f.Layer) ? "SISRUA_VIAS" : f.Layer.Trim();
            string highway = f.Highway?.Trim();

            if (!string.IsNullOrWhiteSpace(highway))
            {
                if (_highwayLayerMap.Value.TryGetValue(highway, out LayerStyle style) && style != null)
                {
                    if (!string.IsNullOrWhiteSpace(style.Layer)) layerName = style.Layer.Trim();
                    return (layerName, style.Aci);
                }

                // Highway conhecido/qualquer: mantém organizado em um layer genérico
                if (layerName.Equals("SISRUA_OSM_VIAS", StringComparison.OrdinalIgnoreCase))
                {
                    layerName = "SISRUA_OSM_OUTROS";
                    return (layerName, 6);
                }
            }

            return (layerName, null);
        }

        private static void NotifyUiJob(JobStatusResponse job)
        {
            try
            {
                SisRuaPalette.PostUiMessage(new
                {
                    action = "JOB_PROGRESS",
                    data = job
                });
            }
            catch (Exception ex)
            {
                Log($"WARN: Error notifying UI job progress: {ex.Message}");
            }
        }

        private static async Task<PrepareResponse> RunPrepareJobAsync(Editor ed, string baseUrl, PrepareJobRequest payload, CancellationToken ct)
        {
            Log($"INFO: Running prepare job for kind: {payload.Kind}");
            string createJson = JsonSerializer.Serialize(payload, _jsonOptions);
            using (var createReq = CreateAuthedJsonRequest(HttpMethod.Post, $"{baseUrl}/api/v1/jobs/prepare", createJson))
            {
                var createResp = await _httpClient.SendAsync(createReq, ct);
                createResp.EnsureSuccessStatusCode();
                string createText = await createResp.Content.ReadAsStringAsync();
                var job = JsonSerializer.Deserialize<JobStatusResponse>(createText, _jsonOptions);
                if (job == null || string.IsNullOrWhiteSpace(job.JobId))
                {
                    throw new InvalidOperationException("Backend retornou resposta inválida ao criar job.");
                }

                NotifyUiJob(job);

                var sw = Stopwatch.StartNew();
                double lastProgress = -1;
                string lastMessage = null;
                string lastStatus = null;

                while (sw.Elapsed < TimeSpan.FromMinutes(10))
                {
                    ct.ThrowIfCancellationRequested();

                    using (var pollReq = CreateAuthedJsonRequest(HttpMethod.Get, $"{baseUrl}/api/v1/jobs/{job.JobId}", jsonBody: null))
                    {
                        var pollResp = await _httpClient.SendAsync(pollReq, ct);
                        pollResp.EnsureSuccessStatusCode();
                        string pollText = await pollResp.Content.ReadAsStringAsync();
                        job = JsonSerializer.Deserialize<JobStatusResponse>(pollText, _jsonOptions);
                        if (job == null)
                        {
                            throw new InvalidOperationException("Backend retornou resposta inválida no polling do job.");
                        }

                        if (!string.Equals(lastStatus, job.Status, StringComparison.OrdinalIgnoreCase) ||
                            Math.Abs(lastProgress - job.Progress) > 0.0001 ||
                            !string.Equals(lastMessage, job.Message, StringComparison.Ordinal))
                        {
                            lastStatus = job.Status;
                            lastProgress = job.Progress;
                            lastMessage = job.Message;

                            ed?.WriteMessage($"\n[sisRUA] Job {job.JobId}: {job.Status} {job.Progress:P0} - {job.Message}");
                            NotifyUiJob(job);
                        }

                        if (string.Equals(job.Status, "completed", StringComparison.OrdinalIgnoreCase))
                        {
                            if (job.Result.ValueKind == JsonValueKind.Undefined || job.Result.ValueKind == JsonValueKind.Null)
                            {
                                throw new InvalidOperationException("Job concluído sem result.");
                            }
                            var result = job.Result.Deserialize<PrepareResponse>(_jsonOptions);
                            Log($"INFO: Job {job.JobId} completed successfully.");
                            return result;
                        }

                        if (string.Equals(job.Status, "failed", StringComparison.OrdinalIgnoreCase))
                        {
                            Log($"ERROR: Job {job.JobId} failed. Error: {job.Error ?? job.Message}");
                            throw new InvalidOperationException(job.Error ?? job.Message ?? "Job falhou no backend.");
                        }
                    }

                    await Task.Delay(500, ct);
                }

                Log($"ERROR: Job {job.JobId} timed out after {sw.Elapsed.TotalMinutes} minutes.");
                throw new TimeoutException("Tempo limite excedido aguardando job do backend.");
            }
        }

        public static async Task ImportarDadosCampo(string geojsonData)
        {
            Editor ed = Application.DocumentManager.MdiActiveDocument.Editor;
            Log("INFO: ImportarDadosCampo called with GeoJSON data.");
            ed.WriteMessage("\n[sisRUA] GeoJSON recebido. Preparando importação (sem DXF)...");

            try
            {
                string baseUrl = GetBackendBaseUrlOrAlert(ed);
                if (string.IsNullOrWhiteSpace(baseUrl)) return;

                ed.WriteMessage("\n[sisRUA] Criando job de importação (GeoJSON) no backend...");
                var jobPayload = new PrepareJobRequest { Kind = "geojson", GeoJson = geojsonData };
                var prepareResponse = await RunPrepareJobAsync(ed, baseUrl, jobPayload, CancellationToken.None);

                if (prepareResponse?.Features == null || prepareResponse.Features.Count == 0)
                {
                    ed.WriteMessage("\n[sisRUA] Aviso: backend retornou 0 features para desenhar.");
                    Log("WARN: Backend returned 0 features to draw.");
                    return;
                }

                ed.WriteMessage($"\n[sisRUA] CRS de saída: {prepareResponse.CrsOut ?? "(desconhecido)"}");
                DrawCadFeatures(prepareResponse.Features);
            }
            catch (HttpRequestException httpEx)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Falha de comunicação com o backend Python. O servidor está rodando? Detalhes: {httpEx.Message}");
                Application.ShowAlertDialog($"Erro de comunicação com o backend do sisRUA.\nVerifique se o plugin foi iniciado corretamente.\n\nDetalhes: {httpEx.Message}");
                Log($"ERROR: HttpRequestException in ImportarDadosCampo: {httpEx.Message}");
            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Ocorreu um erro inesperado durante a importação. Detalhes: {ex.Message}");
                Application.ShowAlertDialog($"Ocorreu um erro inesperado no sisRUA:\n{ex.Message}");
                Log($"FATAL: Unexpected error in ImportarDadosCampo: {ex}");
                Debug.WriteLine($"[sisRUA] StackTrace: {ex}");
            }
        }

        public static async Task GerarProjetoOsm(double latitude, double longitude, double radius)
        {
            Editor ed = Application.DocumentManager.MdiActiveDocument.Editor;
            Log($"INFO: GerarProjetoOsm called with Lat={latitude}, Lon={longitude}, Radius={radius}.");
            ed.WriteMessage("\n[sisRUA] Recebida solicitação para gerar ruas do OSM (sem DXF)...");

            try
            {
                string baseUrl = GetBackendBaseUrlOrAlert(ed);
                if (string.IsNullOrWhiteSpace(baseUrl)) return;

                ed.WriteMessage($"\n[sisRUA] Parâmetros: Lat={latitude}, Lon={longitude}, Raio={radius}m");
                ed.WriteMessage("\n[sisRUA] Criando job OSM no backend...");
                var jobPayload = new PrepareJobRequest
                {
                    Kind = "osm",
                    Latitude = latitude,
                    Longitude = longitude,
                    Radius = radius
                };
                var prepareResponse = await RunPrepareJobAsync(ed, baseUrl, jobPayload, CancellationToken.None);

                if (prepareResponse?.Features == null || prepareResponse.Features.Count == 0)
                {
                    ed.WriteMessage("\n[sisRUA] Aviso: backend retornou 0 features para desenhar.");
                    Log("WARN: Backend returned 0 features to draw.");
                    return;
                }

                ed.WriteMessage($"\n[sisRUA] CRS de saída: {prepareResponse.CrsOut ?? "(desconhecido)"}");
                DrawCadFeatures(prepareResponse.Features);
                EnsureOsmAttributionMText(prepareResponse.Features);
            }
            catch (HttpRequestException httpEx)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Falha de comunicação com o backend Python. O servidor está rodando? Detalhes: {httpEx.Message}");
                Application.ShowAlertDialog($"Erro de comunicação com o backend do sisRUA.\nVerifique se o plugin foi iniciado corretamente.\n\nDetalhes: {httpEx.Message}");
                Log($"ERROR: HttpRequestException in GerarProjetoOsm: {httpEx.Message}");
            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Ocorreu um erro inesperado durante a geração do OSM. Detalhes: {ex.Message}");
                Application.ShowAlertDialog($"Ocorreu um erro inesperado no sisRUA:\n{ex.Message}");
                Log($"FATAL: Unexpected error in GerarProjetoOsm: {ex}");
                Debug.WriteLine($"[sisRUA] StackTrace: {ex}");
            }
        }

        private static void DrawCadFeatures(IEnumerable<CadFeature> features)
        {
            Log("INFO: DrawCadFeatures started.");
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null)
            {
                Log("WARN: DocumentManager.MdiActiveDocument is null in DrawCadFeatures.");
                return;
            }

            Database db = doc.Database;
            Editor ed = doc.Editor;
            double metersToDrawingUnits = GetMetersToDrawingUnitsScale(db);

            using (doc.LockDocument())
            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                LayerTable lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);

                ObjectId msId = SymbolUtilityServices.GetBlockModelSpaceId(db);
                BlockTableRecord ms = (BlockTableRecord)tr.GetObject(msId, OpenMode.ForWrite);

                int createdPolylines = 0;
                int createdBlocks = 0;

                foreach (var f in features)
                {
                    if (f == null) continue;

                    var (layerName, aci) = GetLayerStyleForFeature(f);
                    EnsureLayer(tr, db, lt, layerName, aci);

                    switch (f.FeatureType)
                    {
                        case CadFeatureType.Polyline:
                            if (f.CoordsXy == null || f.CoordsXy.Count < 2) continue;

                            // Desenho de Polylines
                            var centerPolyline = new Polyline();
                            for (int i = 0; i < f.CoordsXy.Count; i++)
                            {
                                var pt = f.CoordsXy[i];
                                if (pt == null || pt.Count < 2) continue;
                                centerPolyline.AddVertexAt(
                                    centerPolyline.NumberOfVertices,
                                    new Autodesk.AutoCAD.Geometry.Point2d(pt[0] * metersToDrawingUnits, pt[1] * metersToDrawingUnits),
                                    0,
                                    0,
                                    0
                                );
                            }

                            if (centerPolyline.NumberOfVertices < 2)
                            {
                                centerPolyline.Dispose();
                                continue;
                            }

                            double? widthUnits = TryGetRoadWidthUnits(f, metersToDrawingUnits);

                            bool drewAsOffsets = false;
                            if (widthUnits.HasValue && widthUnits.Value > 0.05 && IsFinite(widthUnits.Value))
                            {
                                drewAsOffsets = TryAppendOffsetRoadEdges(tr, ms, centerPolyline, widthUnits.Value / 2.0, layerName);
                                if (drewAsOffsets)
                                {
                                    createdPolylines += 2; // bordas esquerda/direita (mínimo)
                                    centerPolyline.Dispose(); // não desenhamos o eixo quando o offset funciona
                                    continue;
                                }
                            }

                            // Fallback: desenha o eixo (e, se houver largura, tenta como polyline com largura constante).
                            if (widthUnits.HasValue && widthUnits.Value > 0.05 && IsFinite(widthUnits.Value))
                            {
                                centerPolyline.ConstantWidth = widthUnits.Value;
                            }
                            centerPolyline.Layer = layerName;
                            centerPolyline.Color = Color.FromColorIndex(ColorMethod.ByLayer, 256);
                            ms.AppendEntity(centerPolyline);
                            tr.AddNewlyCreatedDBObject(centerPolyline, true);
                            createdPolylines++;
                            break;

                        case CadFeatureType.Point:
                            // Inserção de Blocos
                            if (f.InsertionPointXy == null || f.InsertionPointXy.Count < 2 || string.IsNullOrWhiteSpace(f.BlockName) || string.IsNullOrWhiteSpace(f.BlockFilePath))
                            {
                                Log($"WARN: Skipping point feature due to missing data: InsertionPointXy, BlockName, or BlockFilePath is null/empty for feature {f.Name ?? "unnamed"}.");
                                continue;
                            }
                            
                            Autodesk.AutoCAD.Geometry.Point3d insertionPt = new Autodesk.AutoCAD.Geometry.Point3d(
                                f.InsertionPointXy[0] * metersToDrawingUnits,
                                f.InsertionPointXy[1] * metersToDrawingUnits,
                                f.InsertionPointXy.Count > 2 ? f.InsertionPointXy[2] * metersToDrawingUnits : 0.0
                            );

                            InsertBlock(
                                tr, db, ms,
                                f.BlockName, f.BlockFilePath,
                                insertionPt,
                                f.Rotation ?? 0.0,
                                f.Scale ?? 1.0,
                                layerName
                            );
                            createdBlocks++;
                            break;
                    }
                }

                tr.Commit();
                ed.WriteMessage($"\n[sisRUA] Sucesso! {createdPolylines} polylines e {createdBlocks} blocos criados no Model Space.");
                Log($"INFO: DrawCadFeatures completed. {createdPolylines} polylines and {createdBlocks} blocks created.");
                ed.Regen();
            }
        }

        private static void EnsureOsmAttributionMText(IEnumerable<CadFeature> features)
        {
            // ODbL exige atribuição. Além da atribuição no mapa (frontend),
            // colocamos uma anotação no DWG para quando o arquivo for compartilhado.
            try
            {
                Document doc = Application.DocumentManager.MdiActiveDocument;
                if (doc == null)
                {
                    Log("WARN: DocumentManager.MdiActiveDocument is null in EnsureOsmAttributionMText.");
                    return;
                }

                Database db = doc.Database;
                double metersToDrawingUnits = GetMetersToDrawingUnitsScale(db);

                double minX = double.PositiveInfinity, minY = double.PositiveInfinity;
                double maxX = double.NegativeInfinity, maxY = double.NegativeInfinity;

                if (features != null)
                {
                    foreach (var f in features)
                    {
                        if (f?.CoordsXy == null) continue;
                        foreach (var pt in f.CoordsXy)
                        {
                            if (pt == null || pt.Count < 2) continue;
                            double x = pt[0] * metersToDrawingUnits;
                            double y = pt[1] * metersToDrawingUnits;
                            if (!IsFinite(x) || !IsFinite(y)) continue;
                            if (x < minX) minX = x;
                            if (y < minY) minY = y;
                            if (x > maxX) maxX = x;
                            if (y > maxY) maxY = y;
                        }
                    }
                }

                if (!IsFinite(minX) || !IsFinite(minY) || !IsFinite(maxX) || !IsFinite(maxY)) return;

                double span = Math.Max(maxX - minX, maxY - minY);
                // Altura proporcional ao tamanho do resultado (clamp).
                double textHeight = span > 0 ? (span / 500.0) : (10.0 * metersToDrawingUnits);
                double minHeight = 2.0 * metersToDrawingUnits;
                double maxHeight = 50.0 * metersToDrawingUnits;
                if (textHeight < minHeight) textHeight = minHeight;
                if (textHeight > maxHeight) textHeight = maxHeight;

                // Canto superior esquerdo (um pouco para dentro)
                var insPt = new Autodesk.AutoCAD.Geometry.Point3d(minX + textHeight, maxY - textHeight, 0);

                using (doc.LockDocument())
                using (Transaction tr = db.TransactionManager.StartTransaction())
                {
                    LayerTable lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
                    const string layerName = "SISRUA_ATTRIB";
                    EnsureLayer(tr, db, lt, layerName, aci: 7);

                    ObjectId msId = SymbolUtilityServices.GetBlockModelSpaceId(db);
                    BlockTableRecord ms = (BlockTableRecord)tr.GetObject(msId, OpenMode.ForRead);

                    // Evita duplicar se já existe uma atribuição no DWG.
                    foreach (ObjectId id in ms)
                    {
                        var ent = tr.GetObject(id, OpenMode.ForRead) as Entity;
                        if (ent is MText mt)
                        {
                            string t = mt.Contents ?? string.Empty;
                            if (t.IndexOf("OpenStreetMap contributors", StringComparison.OrdinalIgnoreCase) >= 0)
                            {
                                return;
                            }
                        }
                    }

                    ms.UpgradeOpen();
                    var mtext = new MText
                    {
                        Layer = layerName,
                        Color = Color.FromColorIndex(ColorMethod.ByLayer, 256),
                        Location = insPt,
                        TextHeight = textHeight,
                        // MText quebra de linha com \P
                        Contents = "© OpenStreetMap contributors\\Phttps://www.openstreetmap.org/copyright"
                    };

                    ms.AppendEntity(mtext);
                    tr.AddNewlyCreatedDBObject(mtext, true);
                    tr.Commit();
                }
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in EnsureOsmAttributionMText: {ex.Message}");
                // ignore (não pode falhar o fluxo principal)
            }
        }

        private static double? TryGetRoadWidthUnits(CadFeature f, double metersToDrawingUnits)
        {
            try
            {
                // Preferência: backend já estimou width_m.
                if (f != null && f.WidthMeters.HasValue && f.WidthMeters.Value > 0.01 && IsFinite(f.WidthMeters.Value))
                {
                    return f.WidthMeters.Value * metersToDrawingUnits;
                }

                // Fallback local: se width_m não veio, estimamos por tipo de via.
                // Valores são "curb-to-curb" aproximados, em metros.
                string h = f?.Highway?.Trim()?.ToLowerInvariant();
                double? wMeters = null;
                switch (h)
                {
                    case "motorway": wMeters = 20.0; break;
                    case "trunk": wMeters = 16.0; break;
                    case "primary": wMeters = 12.0; break;
                    case "secondary": wMeters = 10.0; break;
                    case "tertiary": wMeters = 9.0; break;
                    case "residential": wMeters = 7.0; break;
                    case "unclassified": wMeters = 7.0; break;
                    case "living_street": wMeters = 6.0; break;
                    case "service": wMeters = 5.0; break;
                    case "footway":
                    case "path":
                    case "cycleway":
                        wMeters = 2.5;
                        break;
                }
                if (!wMeters.HasValue) return null;
                return wMeters.Value * metersToDrawingUnits;
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in TryGetRoadWidthUnits: {ex.Message}");
                return null;
            }
        }

        private static bool TryAppendOffsetRoadEdges(Transaction tr, BlockTableRecord ms, Polyline center, double halfWidthUnits, string layerName)
        {
            try
            {
                if (center == null)
                {
                    Log("WARN: TryAppendOffsetRoadEdges received null center polyline.");
                    return false;
                }
                if (!IsFinite(halfWidthUnits) || halfWidthUnits <= 0.0)
                {
                    Log($"WARN: TryAppendOffsetRoadEdges received invalid halfWidthUnits: {halfWidthUnits}");
                    return false;
                }

                // Offset positivo e negativo. Cada chamada pode retornar múltiplas curvas (geometrias complexas).
                var left = center.GetOffsetCurves(+halfWidthUnits);
                var right = center.GetOffsetCurves(-halfWidthUnits);

                int appended = 0;
                appended += AppendOffsetCurves(tr, ms, left, layerName);
                appended += AppendOffsetCurves(tr, ms, right, layerName);

                // Se não deu nada, falhou.
                return appended >= 2;
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in TryAppendOffsetRoadEdges: {ex.Message}");
                return false;
            }
        }

        private static int AppendOffsetCurves(Transaction tr, BlockTableRecord ms, DBObjectCollection curves, string layerName)
        {
            int appended = 0;
            if (curves == null || curves.Count == 0) return 0;

            foreach (DBObject dbo in curves)
            {
                try
                {
                    if (dbo is Entity ent)
                    {
                        ent.Layer = layerName;
                        ent.Color = Color.FromColorIndex(ColorMethod.ByLayer, 256);
                        ms.AppendEntity(ent);
                        tr.AddNewlyCreatedDBObject(ent, true);
                        appended++;
                    }
                    else
                    {
                        dbo?.Dispose();
                    }
                }
                catch (Exception ex)
                {
                    Log($"WARN: Error appending offset curve: {ex.Message}");
                    try { dbo?.Dispose(); } catch { /* ignore */ }
                }
            }

            return appended;
        }

        private static double GetMetersToDrawingUnitsScale(Database db)
        {
            try
            {
                // Override manual (se necessário): define um fator direto "metros -> unidades do desenho"
                // Ex.: "1000" para mm, "1" para m
                string overrideScale = Environment.GetEnvironmentVariable("SISRUA_M_TO_UNITS");
                if (!string.IsNullOrWhiteSpace(overrideScale))
                {
                    overrideScale = overrideScale.Trim();
                    if (double.TryParse(overrideScale, NumberStyles.Float, CultureInfo.InvariantCulture, out double forced) && forced > 0.0 && IsFinite(forced))
                    {
                        return forced;
                    }
                    // tolera vírgula decimal (pt-BR)
                    string commaFixed = overrideScale.Replace(',', '.');
                    if (double.TryParse(commaFixed, NumberStyles.Float, CultureInfo.InvariantCulture, out forced) && forced > 0.0 && IsFinite(forced))
                    {
                        return forced;
                    }
                }

                // Override persistente (recomendado): %LOCALAPPDATA%\sisRUA\settings.json
                // { "meters_to_units": 1000 }
                double? persisted = SisRuaSettings.TryReadMetersToUnits();
                if (persisted.HasValue)
                {
                    return persisted.Value;
                }

                object v = Application.GetSystemVariable("INSUNITS");
                int insunits = 0;
                if (v is short s) insunits = s;
                else if (v is int i) insunits = i;
                else if (v != null) int.TryParse(v.ToString(), out insunits);

                // https://help.autodesk.com/ (INSUNITS): valores comuns
                // Conversão desejada: metros -> unidade do desenho.
                switch (insunits)
                {
                    case 0: // unitless
                        try
                        {
                            object m = Application.GetSystemVariable("MEASUREMENT");
                            int measurement = 0;
                            if (m is short ms) measurement = ms;
                            else if (m is int mi) measurement = mi;
                            else if (m != null) int.TryParse(m.ToString(), out measurement);
                            // 1 = métrico: por padrão, assume METROS (mais comum em Civil/Topografia).
                            // 0 = imperial: assume inches.
                            return measurement == 1 ? 1.0 : 39.37007874015748;
                        }
                        catch (Exception ex)
                        {
                            Log($"WARN: Error determining MEASUREMENT system variable: {ex.Message}");
                            // fallback: assume metros
                            return 1.0;
                        }
                    case 1: // inches
                        return 39.37007874015748;
                    case 2: // feet
                        return 3.280839895013123;
                    case 3: // miles
                        return 0.0006213711922373339;
                    case 4: // millimeters
                        return 1000.0;
                    case 5: // centimeters
                        return 100.0;
                    case 6: // meters
                        return 1.0;
                    case 7: // kilometers
                        return 0.001;
                    default:
                        // desconhecido: não arrisca
                        return 1.0;
                }
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in GetMetersToDrawingUnitsScale: {ex.Message}");
            }
            return 1.0;
        }

        private static bool IsFinite(double x)
        {
            return !(double.IsNaN(x) || double.IsInfinity(x));
        }

        private static void EnsureLayer(Transaction tr, Database db, LayerTable lt, string layerName, short? aci = null)
        {
            if (lt.Has(layerName)) return;

            try
            {
                lt.UpgradeOpen();
                var ltr = new LayerTableRecord { Name = layerName };
                if (aci.HasValue)
                {
                    ltr.Color = Color.FromColorIndex(ColorMethod.ByAci, aci.Value);
                }
                lt.Add(ltr);
                tr.AddNewlyCreatedDBObject(ltr, true);
                Log($"INFO: Created new layer: {layerName}");
            }
            catch (Exception ex)
            {
                Log($"ERROR: Failed to create layer {layerName}: {ex.Message}");
            }
        }

        // DXF foi descontinuado no fluxo padrão (JSON → polylines).
    }
}