using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading.Tasks;
using sisRUA.UI;
using sisRUA.Core.DTOs;
using sisRUA.Engine;

namespace sisRUA
{
    public class SisRuaCommands
    {
        // Dependency Injection for the Engine
        public static IDrawingEngine Engine { get; set; } = new AutoCADDrawingEngine();

        private static readonly HttpClient _httpClient = new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
        private static readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions { PropertyNameCaseInsensitive = true };
        private static ProjectRepository _projectRepository = new ProjectRepository();

        private static IEnumerable<CadFeatureDto> _lastDrawnFeatures;
        private static string _lastDrawnCrsOut;

        [CommandMethod("SISRUA_RUN_QA", CommandFlags.Session)]
        public static void SisRuaRunQaCommand()
        {
            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                string localDir = SisRuaPlugin.GetLocalSisRuaDir() ?? Path.GetTempPath();
                string qaPath = Path.Combine(localDir, "qa", "out", "geometry_compliance.xml");
                GeometryComplianceTests.RunAndExport(qaPath);
                doc.Editor.WriteMessage($"\n[sisRUA] QA Integridade Concluído: {qaPath}");
            });
        }

        [CommandMethod("SISRUA_HEADLESS_SMOKE", CommandFlags.Session)]
        public static void SisRuaHeadlessSmokeCommand()
        {
            Editor ed = Application.DocumentManager.MdiActiveDocument.Editor;
            try
            {
                ed.WriteMessage("\n[sisRUA] Iniciando SMOKE TEST Headless...");
                
                // 1. Verificar se o backend está pronto (esperar até 10s se necessário)
                var mgr = SisRuaPlugin.Instance?.BackendManager;
                int retry = 0;
                while ((mgr == null || !mgr.IsReady) && retry < 20) 
                {
                    ed.WriteMessage("."); // Feedback visual no console
                    System.Threading.Thread.Sleep(500);
                    retry++;
                }

                if (mgr == null || !mgr.IsReady)
                {
                    ed.WriteMessage("\n[FAIL] Backend não está pronto para o teste após aguardar.");
                    return;
                }

                ed.WriteMessage($"\n[sisRUA] Backend OK: {mgr.BaseUrl}");

                // 2. Simular uma operação simples do Engine (sem UI)
                // Criamos uma entidade de teste via Shield para garantir transação
                SisRuaTransactionalShield.Execute((doc, db, tr) => {
                    var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                    var btr = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
                    
                    var line = new Line(new Point3d(0,0,0), new Point3d(10,10,0));
                    line.Layer = "0";
                    btr.AppendEntity(line);
                    tr.AddNewlyCreatedDBObject(line, true);
                });

                ed.WriteMessage("\n[sisRUA] Entidade de teste desenhada com sucesso.");
                ed.WriteMessage("\nTEST_SUCCESS"); // Sinal para o orquestrador
            }
            catch (System.Exception ex)
            {
                ed.WriteMessage($"\n[FAIL] Erro no Smoke Test: {ex.Message}");
            }
        }

        [CommandMethod("SISRUA_SAVE_PROJECT", CommandFlags.Session)]
        public static void SisRuaSaveProjectCommand()
        {
            if (_lastDrawnFeatures == null || !_lastDrawnFeatures.Any())
            {
                Application.ShowAlertDialog("Nenhum dado recente para salvar. Desenhe algo primeiro com SISRUA.");
                return;
            }

            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                Editor ed = doc.Editor;
                PromptStringOptions psoId = new PromptStringOptions("\n[sisRUA] ID do projeto (deixe em branco para gerar):") { AllowSpaces = false };
                string projectId = ed.GetString(psoId).StringResult.Trim();
                if (string.IsNullOrEmpty(projectId)) projectId = DateTime.Now.ToString("yyyyMMddHHmmss");

                PromptStringOptions psoName = new PromptStringOptions($"\n[sisRUA] Nome do projeto:");
                string projectName = ed.GetString(psoName).StringResult.Trim();
                if (string.IsNullOrEmpty(projectName)) projectName = $"Projeto {projectId}";

                _projectRepository.SaveProject(projectId, projectName, _lastDrawnCrsOut, _lastDrawnFeatures);
                ed.WriteMessage($"\n[sisRUA] Projeto '{projectName}' salvo localmente.");
                
                // Audit metadata is injected into the DWG for compliance signing
                Engine.InjectAuditMetadata(projectId);
            });
        }

        [CommandMethod("SISRUA_RELOAD_PROJECT", CommandFlags.Session)]
        public static async void SisRuaReloadProjectCommand()
        {
            await SisRuaTransactionalShield.ExecuteAsync(async (doc, db, tr) =>
            {
                var ed = doc.Editor;
                var projects = _projectRepository.ListProjects();
                if (!projects.Any()) { Application.ShowAlertDialog("Não há projetos salvos."); return; }

                PromptStringOptions pso = new PromptStringOptions("\n[sisRUA] ID do projeto a carregar:") { AllowSpaces = false };
                string selectedProjectId = ed.GetString(pso).StringResult.Trim();
                
                var (projectName, crsOut, features) = _projectRepository.LoadProject(selectedProjectId);
                if (features == null || !features.Any()) { Application.ShowAlertDialog("Projeto não encontrado."); return; }

                using (var dlg = new ProcessingDialog())
                {
                    Application.ShowModelessDialog(dlg);
                    await Engine.DrawFeaturesAsync(features, crsOut, dlg);
                }
                
                _lastDrawnFeatures = features;
                _lastDrawnCrsOut = crsOut;
            });
        }

        public static async Task ImportarDadosCampo(string geojsonData)
        {
            await SisRuaTransactionalShield.ExecuteAsync(async (doc, db, tr) =>
            {
                var ed = doc.Editor;
                string baseUrl = GetBackendBaseUrlOrAlert(ed);
                if (baseUrl == null) return;

                var jobPayload = new PrepareJobRequest { Kind = "geojson", GeoJson = geojsonData };
                using (var dlg = new ProcessingDialog())
                {
                    Application.ShowModelessDialog(dlg);
                    var response = await RunPrepareJobAsync(ed, baseUrl, jobPayload, dlg);
                    if (response?.Features != null && response.Features.Any())
                    {
                        await Engine.DrawFeaturesAsync(response.Features, response.CrsOut, dlg);
                        _lastDrawnFeatures = response.Features;
                        _lastDrawnCrsOut = response.CrsOut;
                    }
                }
            });
        }

        public static async Task GerarProjetoOsm(double lat, double lon, double rad)
        {
            await SisRuaTransactionalShield.ExecuteAsync(async (doc, db, tr) =>
            {
                var ed = doc.Editor;
                string baseUrl = GetBackendBaseUrlOrAlert(ed);
                if (baseUrl == null) return;

                var jobPayload = new PrepareJobRequest { Kind = "osm", Latitude = lat, Longitude = lon, Radius = rad };
                using (var dlg = new ProcessingDialog())
                {
                    Application.ShowModelessDialog(dlg);
                    var response = await RunPrepareJobAsync(ed, baseUrl, jobPayload, dlg);
                    if (response?.Features != null && response.Features.Any())
                    {
                        await Engine.DrawFeaturesAsync(response.Features, response.CrsOut, dlg);
                        _lastDrawnFeatures = response.Features;
                        _lastDrawnCrsOut = response.CrsOut;
                    }
                }
            });
        }

        private static async Task<PrepareResponse> RunPrepareJobAsync(Editor ed, string baseUrl, PrepareJobRequest payload, ProcessingDialog dlg)
        {
            string createJson = JsonSerializer.Serialize(payload, _jsonOptions);
            var createReq = CreateAuthedJsonRequest(HttpMethod.Post, $"{baseUrl}/api/v1/jobs/prepare", createJson);
            var createResp = await _httpClient.SendAsync(createReq);
            createResp.EnsureSuccessStatusCode();

            var job = JsonSerializer.Deserialize<JobStatusResponse>(await createResp.Content.ReadAsStringAsync(), _jsonOptions);
            
            while (true)
            {
                if (dlg.WasCancelled)
                {
                    await _httpClient.SendAsync(CreateAuthedJsonRequest(HttpMethod.Delete, $"{baseUrl}/api/v1/jobs/{job.JobId}", null));
                    throw new OperationCanceledException();
                }

                var pollResp = await _httpClient.SendAsync(CreateAuthedJsonRequest(HttpMethod.Get, $"{baseUrl}/api/v1/jobs/{job.JobId}", null));
                job = JsonSerializer.Deserialize<JobStatusResponse>(await pollResp.Content.ReadAsStringAsync(), _jsonOptions);

                if (job.Status == "completed") return job.Result.Deserialize<PrepareResponse>(_jsonOptions);
                if (job.Status == "failed") throw new System.Exception(job.Error ?? "Job failed");

                await Task.Delay(1000);
            }
        }

        private static string GetBackendBaseUrlOrAlert(Editor ed)
        {
            var mgr = SisRuaPlugin.Instance?.BackendManager;
            if (mgr == null) 
            {
                Application.ShowAlertDialog("Erro: Gerenciador de Backend não instanciado.");
                return null;
            }

            if (mgr.IsInitializing)
            {
                ed.WriteMessage("\n[sisRUA] O backend está inicializando. Por favor, aguarde alguns segundos...");
                return null;
            }

            if (!mgr.IsReady)
            {
                if (mgr.LastError != null)
                {
                    Application.ShowAlertDialog($"O backend falhou ao iniciar: {mgr.LastError.Message}");
                }
                else
                {
                    Application.ShowAlertDialog("O backend não está pronto. Tente novamente em instantes.");
                }
                return null;
            }

            return mgr.BaseUrl;
        }

        private static HttpRequestMessage CreateAuthedJsonRequest(HttpMethod method, string url, string body)
        {
            var req = new HttpRequestMessage(method, url);
            if (!string.IsNullOrEmpty(SisRuaPlugin.BackendAuthToken))
                req.Headers.TryAddWithoutValidation(SisRuaPlugin.BackendAuthHeaderName, SisRuaPlugin.BackendAuthToken);
            if (body != null) req.Content = new StringContent(body, Encoding.UTF8, "application/json");
            return req;
        }

        // --- DTOs for Backend Communication ---
        private sealed class PrepareJobRequest { public string Kind { get; set; } public double? Latitude { get; set; } public double? Longitude { get; set; } public double? Radius { get; set; } public string GeoJson { get; set; } }
        private sealed class JobStatusResponse { public string JobId { get; set; } public string Status { get; set; } public double Progress { get; set; } public string Message { get; set; } public JsonElement Result { get; set; } public string Error { get; set; } }
        private sealed class PrepareResponse { public string CrsOut { get; set; } public List<CadFeatureDto> Features { get; set; } }
    }
}