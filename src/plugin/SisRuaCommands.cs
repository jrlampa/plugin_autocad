// SisRuaCommands.cs — ponto de entrada: campos compartilhados e comandos AutoCAD.
// Arquivo dividido em partial class para manter cada módulo abaixo de 500 linhas (SoC):
//   Commands/SisRuaCommandDtos.cs   — DTOs HTTP privados
//   Commands/SisRuaCommandConfig.cs — mapeamento de layers e blocos
//   Commands/SisRuaCadUtils.cs      — utilitários CAD (bloco, layer, escala, HTTP)
//   Commands/SisRuaDrawHelpers.cs   — lógica de desenho e metadados BIM-LITE
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

namespace sisRUA
{
    using sisRUA.Core.DTOs;
    using sisRUA.UI;
    using Exception = System.Exception;

    /// <summary>
    /// Comandos AutoCAD do sisRUA e estado compartilhado do plugin.
    /// Implementação distribuída em partial class — consulte Commands/*.cs para os detalhes.
    /// </summary>
    public partial class SisRuaCommands
    {
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

        // Dependency Injection for Testing
        public static sisRUA.Engine.IDrawingEngine Engine { get; set; } = new sisRUA.Engine.AutoCADDrawingEngine();

        // BIM-LITE: Cache the last imported features to allow explicit saving
        private static List<CadFeatureDto> _lastImportedFeatures = new List<CadFeatureDto>();

        private static readonly HttpClient _httpClient = new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
        private static readonly JsonSerializerOptions _jsonOptions = new JsonSerializerOptions
        {
            PropertyNameCaseInsensitive = true
        };
        private static ProjectRepository _projectRepository = new ProjectRepository(); // Instantiate the repository

        private static IEnumerable<CadFeatureDto> _lastDrawnFeatures; // Store features from last drawing operation
        private static string _lastDrawnCrsOut; // Store CRS from last drawing operation

        [CommandMethod("SISRUA_SAVE_PROJECT", CommandFlags.Session)]
        public static void SisRuaSaveProjectCommand()
        {
            if (_lastDrawnFeatures == null || !_lastDrawnFeatures.Any())
            {
                Log("WARN: SISRUA_SAVE_PROJECT called but no features were drawn since last AutoCAD session or command.");
                Application.ShowAlertDialog("Nenhum dado recente para salvar. Desenhe algo primeiro com SISRUA.");
                return;
            }

            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                Editor ed = doc.Editor;

                PromptStringOptions psoId = new PromptStringOptions("\n[sisRUA] Digite o ID do projeto (ex: A001, deixe em branco para gerar):")
                {
                    AllowSpaces = false
                };
                PromptResult resId = ed.GetString(psoId);
                string projectId = resId.StringResult.Trim();

                if (string.IsNullOrWhiteSpace(projectId))
                {
                    projectId = DateTime.Now.ToString("yyyyMMddHHmmss");
                    ed.WriteMessage($"\n[sisRUA] ID de projeto gerado automaticamente: {projectId}");
                }

                PromptStringOptions psoName = new PromptStringOptions($"\n[sisRUA] Digite o nome do projeto (opcional, padrão: 'Projeto {projectId}'):");
                PromptResult resName = ed.GetString(psoName);
                string projectName = string.IsNullOrWhiteSpace(resName.StringResult) ? $"Projeto {projectId}" : resName.StringResult.Trim();

                _projectRepository.SaveProject(projectId, projectName, _lastDrawnCrsOut, _lastDrawnFeatures);
                ed.WriteMessage($"\n[sisRUA] Projeto '{projectName}' (ID: {projectId}) salvo com sucesso.");
                
                _lastDrawnFeatures = null;
                _lastDrawnCrsOut = null;
            });
        }

        [CommandMethod("SISRUA_RELOAD_PROJECT", CommandFlags.Session)]
        public static async void SisRuaReloadProjectCommand()
        {
            await SisRuaTransactionalShield.ExecuteAsync(async (doc, db, tr) =>
            {
                Editor ed = doc.Editor;
                
                try
                {
                    var projects = _projectRepository.ListProjects();
                    if (!projects.Any())
                    {
                        Application.ShowAlertDialog("Não há projetos salvos para carregar.");
                        ed.WriteMessage("\n[sisRUA] Nenhum projeto salvo encontrado.");
                        return;
                    }

                    ed.WriteMessage("\n--- Projetos Salvos ---");
                    foreach (var p in projects)
                    {
                        ed.WriteMessage($"\nID: {p.projectId}, Nome: {p.projectName}, Data: {p.creationDate}");
                    }
                    ed.WriteMessage("\n---------------------");

                    PromptStringOptions pso = new PromptStringOptions("\n[sisRUA] Digite o ID do projeto a carregar:")
                    {
                        AllowSpaces = false
                    };
                    PromptResult res = ed.GetString(pso);
                    if (res.Status != PromptStatus.OK)
                    {
                        ed.WriteMessage("\n[sisRUA] Operação de carregamento cancelada.");
                        return;
                    }

                    string selectedProjectId = res.StringResult.Trim();
                    var (projectName, crsOut, features) = _projectRepository.LoadProject(selectedProjectId);

                    if (features == null || !features.Any())
                    {
                        Application.ShowAlertDialog($"Projeto '{selectedProjectId}' não encontrado ou vazio.");
                        ed.WriteMessage($"\n[sisRUA] Projeto '{selectedProjectId}' não encontrado ou vazio.");
                        return;
                    }

                    ed.WriteMessage($"\n[sisRUA] Carregando e redesenhando projeto '{projectName}' (ID: {selectedProjectId})...");
                    using (var dlg = new ProcessingDialog())
                    {
                        Autodesk.AutoCAD.ApplicationServices.Application.ShowModelessDialog(dlg);
                        Engine.WriteMessage($"Reloading project {selectedProjectId}...");
                        await DrawCadFeatureDtos(features, dlg);
                    }
                    
                    _lastDrawnFeatures = features;
                    _lastDrawnCrsOut = crsOut;

                    ed.WriteMessage($"\n[sisRUA] Projeto '{projectName}' redesenhado com sucesso.");
                }
                catch (System.Exception ex)
                {
                    Log($"ERROR: Failed to load project: {ex.Message}");
                    Application.ShowAlertDialog($"Erro ao carregar projeto: {ex.Message}");
                }
            });
        }

        [CommandMethod("SISRUA_SYNC_CLOUD", CommandFlags.Modal)]
        public async void SisRuaSyncCloudCommand()
        {
            await SisRuaTransactionalShield.ExecuteAsync(async (doc, db, tr) =>
            {
                var ed = doc.Editor;
                string baseUrl = GetBackendBaseUrlOrAlert(ed);
                if (baseUrl == null) return;

                ed.WriteMessage("\n[sisRUA] Iniciando sincronização com sisRUA Cloud (Enterprise Node)...");

                try
                {
                    using (var req = CreateAuthedJsonRequest(HttpMethod.Post, $"{baseUrl}/api/v1/sync/cloud", null))
                    {
                        var resp = await _httpClient.SendAsync(req);
                        resp.EnsureSuccessStatusCode();
                        string text = await resp.Content.ReadAsStringAsync();
                        var syncResult = JsonSerializer.Deserialize<SyncToCloudResponse>(text, _jsonOptions);

                        if (syncResult != null && syncResult.Status == "success")
                        {
                            ed.WriteMessage($"\n[sisRUA] Sucesso! {syncResult.SyncedFeatures} entidades sincronizadas com {syncResult.CloudNode}.");
                            ed.WriteMessage("\n[sisRUA] Backup e integridade de dados verificados (Audit Grade).");
                        }
                        else
                        {
                            ed.WriteMessage("\n[sisRUA] Falha na sincronização. Verifique sua licença Enterprise.");
                        }
                    }
                }
                catch (Exception ex)
                {
                    ed.WriteMessage($"\n[sisRUA] Erro de conexão: {ex.Message}");
                    Log($"ERROR: Cloud Sync failed: {ex.Message}");
                }
            });
        }

        // ──────────────────────────────────────────────────────────────────────────
        // API pública: chamada pela paleta WebView2 via PostWebMessageAsJson
        // ──────────────────────────────────────────────────────────────────────────

        /// <summary>
        /// Importa um GeoJSON recebido via Drag &amp; Drop na paleta para o desenho atual.
        /// </summary>
        public static async Task ImportarDadosCampo(string geojsonData)
        {
            await SisRuaTransactionalShield.ExecuteAsync(async (doc, db, tr) =>
            {
                var ed = doc.Editor;
                Log("INFO: ImportarDadosCampo called with GeoJSON data.");
                ed.WriteMessage("\n[sisRUA] GeoJSON recebido. Preparando importação...");

                try
                {
                    string baseUrl = GetBackendBaseUrlOrAlert(ed);
                    if (string.IsNullOrWhiteSpace(baseUrl)) return;

                    var jobPayload = new PrepareJobRequest { Kind = "geojson", GeoJson = geojsonData };
                    using (var dlg = new ProcessingDialog())
                    {
                        Application.ShowModelessDialog(dlg);
                        var prepareResponse = await RunPrepareJobAsync(ed, baseUrl, jobPayload, dlg);
                        if (prepareResponse?.Features == null || prepareResponse.Features.Count == 0)
                        {
                            ed.WriteMessage("\n[sisRUA] Aviso: backend retornou 0 features para desenhar.");
                            return;
                        }

                        ed.WriteMessage($"\n[sisRUA] CRS de saída: {prepareResponse.CrsOut ?? "(desconhecido)"}");
                        await DrawCadFeatureDtos(prepareResponse.Features, dlg);
                        _lastDrawnFeatures = prepareResponse.Features;
                        _lastDrawnCrsOut = prepareResponse.CrsOut;
                    }
                }
                catch (HttpRequestException httpEx)
                {
                    Log($"ERROR: HttpRequestException em ImportarDadosCampo: {httpEx.Message}");
                    throw;
                }
                catch (Exception ex)
                {
                    Log($"FATAL: Erro inesperado em ImportarDadosCampo: {ex}");
                    throw;
                }
            });
        }

        /// <summary>
        /// Gera ruas do OSM para a coordenada e raio indicados.
        /// </summary>
        public static async Task GerarProjetoOsm(double latitude, double longitude, double radius)
        {
            await SisRuaTransactionalShield.ExecuteAsync(async (doc, db, tr) =>
            {
                var ed = doc.Editor;
                Log($"INFO: GerarProjetoOsm Lat={latitude}, Lon={longitude}, Radius={radius}.");
                ed.WriteMessage("\n[sisRUA] Gerando ruas do OSM...");

                try
                {
                    string baseUrl = GetBackendBaseUrlOrAlert(ed);
                    if (string.IsNullOrWhiteSpace(baseUrl)) return;

                    var jobPayload = new PrepareJobRequest
                    {
                        Kind = "osm",
                        Latitude = latitude,
                        Longitude = longitude,
                        Radius = radius
                    };

                    using (var dlg = new ProcessingDialog())
                    {
                        Application.ShowModelessDialog(dlg);
                        var prepareResponse = await RunPrepareJobAsync(ed, baseUrl, jobPayload, dlg);
                        if (prepareResponse?.Features == null || prepareResponse.Features.Count == 0)
                        {
                            ed.WriteMessage("\n[sisRUA] Aviso: backend retornou 0 features para desenhar.");
                            return;
                        }

                        ed.WriteMessage($"\n[sisRUA] CRS de saída: {prepareResponse.CrsOut ?? "(desconhecido)"}");
                        await DrawCadFeatureDtos(prepareResponse.Features, dlg);
                        EnsureOsmAttributionMText(prepareResponse.Features);
                        _lastDrawnFeatures = prepareResponse.Features;
                        _lastDrawnCrsOut = prepareResponse.CrsOut;
                    }
                }
                catch (HttpRequestException httpEx)
                {
                    Log($"ERROR: HttpRequestException em GerarProjetoOsm: {httpEx.Message}");
                    throw;
                }
                catch (Exception ex)
                {
                    Log($"FATAL: Erro inesperado em GerarProjetoOsm: {ex}");
                    throw;
                }
            });
        }
    }
}
