using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
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

        public static async Task ImportarDadosCampo(string geojsonData)
        {
            Editor ed = Application.DocumentManager.MdiActiveDocument.Editor;
            ed.WriteMessage("\n[sisRUA] GeoJSON recebido. Preparando importação (sem DXF)...");

            try
            {
                string baseUrl = GetBackendBaseUrlOrAlert(ed);
                if (string.IsNullOrWhiteSpace(baseUrl)) return;

                var payload = new PrepareGeoJsonRequest { GeoJson = geojsonData };
                string jsonPayload = JsonSerializer.Serialize(payload, _jsonOptions);
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                ed.WriteMessage("\n[sisRUA] Enviando GeoJSON para o backend Python (projeção CRS/UTM + extração de linhas)...");
                var response = await _httpClient.PostAsync($"{baseUrl}/api/v1/prepare/geojson", content);
                response.EnsureSuccessStatusCode();

                string jsonResponse = await response.Content.ReadAsStringAsync();
                var prepareResponse = JsonSerializer.Deserialize<PrepareResponse>(jsonResponse, _jsonOptions);

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

                var requestData = new PrepareOsmRequest
                {
                    Latitude = latitude,
                    Longitude = longitude,
                    Radius = radius
                };

                string jsonPayload = JsonSerializer.Serialize(requestData, _jsonOptions);
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");

                ed.WriteMessage("\n[sisRUA] Enviando solicitação para o backend Python...");
                
                var response = await _httpClient.PostAsync($"{baseUrl}/api/v1/prepare/osm", content);
                response.EnsureSuccessStatusCode();

                string jsonResponse = await response.Content.ReadAsStringAsync();
                var prepareResponse = JsonSerializer.Deserialize<PrepareResponse>(jsonResponse, _jsonOptions);

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

                    string layerName = string.IsNullOrWhiteSpace(f.Layer) ? "SISRUA_VIAS" : f.Layer.Trim();
                    EnsureLayer(tr, db, lt, layerName);

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
                    ms.AppendEntity(pl);
                    tr.AddNewlyCreatedDBObject(pl, true);
                    created++;
                }

                tr.Commit();
                ed.WriteMessage($"\n[sisRUA] Sucesso! {created} polylines criadas no Model Space.");
                ed.Regen();
            }
        }

        private static void EnsureLayer(Transaction tr, Database db, LayerTable lt, string layerName)
        {
            if (lt.Has(layerName)) return;

            lt.UpgradeOpen();
            var ltr = new LayerTableRecord { Name = layerName };
            lt.Add(ltr);
            tr.AddNewlyCreatedDBObject(ltr, true);
        }

        public static void ImportDxf(string dxfFilePath)
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return; 
            
            Database db = doc.Database;
            Editor ed = doc.Editor;

            using (doc.LockDocument())
            {
                using (var dxfDb = new Database(false, true))
                {
                    try
                    {
                        ed.WriteMessage($"\n[sisRUA] Importando entidades do arquivo DXF...");
                        dxfDb.DxfIn(dxfFilePath, null);

                        using (Transaction tr = db.TransactionManager.StartTransaction())
                        {
                            var sourceMsId = SymbolUtilityServices.GetBlockModelSpaceId(dxfDb);
                            var destMsId = SymbolUtilityServices.GetBlockModelSpaceId(db);

                            var sourceMs = (BlockTableRecord)tr.GetObject(sourceMsId, OpenMode.ForRead);
                            
                            var objectsToClone = new ObjectIdCollection();
                            foreach (ObjectId objId in sourceMs)
                            {
                                objectsToClone.Add(objId);
                            }

                            if (objectsToClone.Count > 0)
                            {
                                var idMap = new IdMapping();
                                db.WblockCloneObjects(objectsToClone, destMsId, idMap, DuplicateRecordCloning.Replace, false);
                                ed.WriteMessage($"\n[sisRUA] Sucesso! {objectsToClone.Count} entidades importadas para o Model Space.");
                                ed.Regen();
                            }
                            else
                            {
                                ed.WriteMessage("\n[sisRUA] Aviso: Nenhuma entidade foi encontrada no arquivo DXF para importar.");
                            }
                            tr.Commit();
                        }
                    }
                    catch (System.Exception ex)
                    {
                        ed.WriteMessage($"\n[sisRUA] ERRO: Falha crítica durante a importação do DXF: {ex.Message}");
                    }
                }
            }
        }
    }
}