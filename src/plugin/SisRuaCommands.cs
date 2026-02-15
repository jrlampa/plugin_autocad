using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
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
                ed.WriteMessage($"\n[sisRUA] Projeto '{projectName}' salvo.");
                
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
            string url = SisRuaPlugin.BackendBaseUrl;
            if (string.IsNullOrEmpty(url)) Application.ShowAlertDialog("Backend não inicializado.");
            return url;
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