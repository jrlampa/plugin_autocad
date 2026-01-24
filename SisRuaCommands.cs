using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
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

        private static string GetBackendBaseUrlOrAlert(Editor ed)
        {
            string baseUrl = SisRuaPlugin.BackendBaseUrl;
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                ed?.WriteMessage("\n[sisRUA] ERRO: BackendBaseUrl não definido. O plugin inicializou corretamente?");
                Application.ShowAlertDialog("Backend do sisRUA não foi inicializado corretamente.\nFeche e reabra o AutoCAD e execute o comando SISRUA novamente.");
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
            [JsonPropertyName("layer")]
            public string Layer { get; set; }

            [JsonPropertyName("name")]
            public string Name { get; set; }

            [JsonPropertyName("highway")]
            public string Highway { get; set; }

            [JsonPropertyName("coords_xy")]
            public List<List<double>> CoordsXy { get; set; }
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
            catch
            {
                // ignore
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
            catch
            {
                // ignore
            }
        }

        private static async Task<PrepareResponse> RunPrepareJobAsync(Editor ed, string baseUrl, PrepareJobRequest payload, CancellationToken ct)
        {
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
                            return result;
                        }

                        if (string.Equals(job.Status, "failed", StringComparison.OrdinalIgnoreCase))
                        {
                            throw new InvalidOperationException(job.Error ?? job.Message ?? "Job falhou no backend.");
                        }
                    }

                    await Task.Delay(500, ct);
                }

                throw new TimeoutException("Tempo limite excedido aguardando job do backend.");
            }
        }

        public static async Task ImportarDadosCampo(string geojsonData)
        {
            Editor ed = Application.DocumentManager.MdiActiveDocument.Editor;
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
                    return;
                }

                ed.WriteMessage($"\n[sisRUA] CRS de saída: {prepareResponse.CrsOut ?? "(desconhecido)"}");
                DrawPolylines(prepareResponse.Features);
            }
            catch (HttpRequestException httpEx)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Falha de comunicação com o backend Python. O servidor está rodando? Detalhes: {httpEx.Message}");
                Application.ShowAlertDialog($"Erro de comunicação com o backend do sisRUA.\nVerifique se o plugin foi iniciado corretamente.\n\nDetalhes: {httpEx.Message}");
            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Ocorreu um erro inesperado durante a importação. Detalhes: {ex.Message}");
                Application.ShowAlertDialog($"Ocorreu um erro inesperado no sisRUA:\n{ex.Message}");
                Debug.WriteLine($"[sisRUA] StackTrace: {ex}");
            }
        }

        public static async Task GerarProjetoOsm(double latitude, double longitude, double radius)
        {
            Editor ed = Application.DocumentManager.MdiActiveDocument.Editor;
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
                    return;
                }

                ed.WriteMessage($"\n[sisRUA] CRS de saída: {prepareResponse.CrsOut ?? "(desconhecido)"}");
                DrawPolylines(prepareResponse.Features);
            }
            catch (HttpRequestException httpEx)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Falha de comunicação com o backend Python. O servidor está rodando? Detalhes: {httpEx.Message}");
                Application.ShowAlertDialog($"Erro de comunicação com o backend do sisRUA.\nVerifique se o plugin foi iniciado corretamente.\n\nDetalhes: {httpEx.Message}");
            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\n[sisRUA] ERRO: Ocorreu um erro inesperado durante a geração do OSM. Detalhes: {ex.Message}");
                Application.ShowAlertDialog($"Ocorreu um erro inesperado no sisRUA:\n{ex.Message}");
                Debug.WriteLine($"[sisRUA] StackTrace: {ex}");
            }
        }

        private static void DrawPolylines(IEnumerable<CadFeature> features)
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return;

            Database db = doc.Database;
            Editor ed = doc.Editor;

            using (doc.LockDocument())
            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                LayerTable lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);

                ObjectId msId = SymbolUtilityServices.GetBlockModelSpaceId(db);
                BlockTableRecord ms = (BlockTableRecord)tr.GetObject(msId, OpenMode.ForWrite);

                int created = 0;
                foreach (var f in features)
                {
                    if (f?.CoordsXy == null || f.CoordsXy.Count < 2) continue;

                    var (layerName, aci) = GetLayerStyleForFeature(f);
                    EnsureLayer(tr, db, lt, layerName, aci);

                    var pl = new Polyline();
                    for (int i = 0; i < f.CoordsXy.Count; i++)
                    {
                        var pt = f.CoordsXy[i];
                        if (pt == null || pt.Count < 2) continue;
                        pl.AddVertexAt(pl.NumberOfVertices, new Autodesk.AutoCAD.Geometry.Point2d(pt[0], pt[1]), 0, 0, 0);
                    }

                    if (pl.NumberOfVertices < 2)
                    {
                        pl.Dispose();
                        continue;
                    }

                    pl.Layer = layerName;
                    pl.Color = Color.FromColorIndex(ColorMethod.ByLayer, 256);
                    ms.AppendEntity(pl);
                    tr.AddNewlyCreatedDBObject(pl, true);
                    created++;
                }

                tr.Commit();
                ed.WriteMessage($"\n[sisRUA] Sucesso! {created} polylines criadas no Model Space.");
                ed.Regen();
            }
        }

        private static void EnsureLayer(Transaction tr, Database db, LayerTable lt, string layerName, short? aci = null)
        {
            if (lt.Has(layerName)) return;

            lt.UpgradeOpen();
            var ltr = new LayerTableRecord { Name = layerName };
            if (aci.HasValue)
            {
                ltr.Color = Color.FromColorIndex(ColorMethod.ByAci, aci.Value);
            }
            lt.Add(ltr);
            tr.AddNewlyCreatedDBObject(ltr, true);
        }

        // DXF foi descontinuado no fluxo padrão (JSON → polylines).
    }
}