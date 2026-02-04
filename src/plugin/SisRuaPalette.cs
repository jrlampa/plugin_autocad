using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using Autodesk.AutoCAD.Windows;
using Autodesk.AutoCAD.DatabaseServices;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.Json;
using System.Windows.Forms;
using System.Threading;
using System.Threading.Tasks;

namespace sisRUA
{
    /// <summary>
    /// Gerencia a PaletteSet (a janela flutuante) que hospeda a interface web (WebView2).
    /// </summary>
    public class SisRuaPalette
    {
        private static PaletteSet _paletteSet;
        private static WebView2 _webView;
        private static Panel _splashPanel;
        private static Label _splashLabel;
        private static System.Windows.Forms.Timer _splashTimer;
        private static int _messageIndex = 0;
        private static readonly string[] _loadingMessages = new[]
        {
            "Sintonizando o rádio do estagiário...",
            "Pedindo aumento pro Zaluar...",
            "Perguntando pro André algo cabuloso...",
            "Limpando o cache do AutoCAD (quem dera)...",
            "Calibrando o GPS de papel...",
            "Engraxando os eixos das ruas...",
            "Convencendo os pixels a ficarem no lugar...",
            "Aguardando o café do backend ficar pronto..."
        };
        private static Control _uiInvokeTarget;

        public static void PostUiMessage(object message)
        {
            try
            {
                if (message == null) return;
                string json = JsonSerializer.Serialize(message);

                var target = _uiInvokeTarget;
                if (target != null && target.IsHandleCreated)
                {
                    target.BeginInvoke((Action)(() =>
                    {
                        _webView?.CoreWebView2?.PostWebMessageAsString(json);
                    }));
                }
                else
                {
                    _webView?.CoreWebView2?.PostWebMessageAsString(json);
                }
            }
            catch
            {
                // ignore
            }
        }

        [CommandMethod("SISRUA", CommandFlags.Session)]
        public void ShowSisRuaPalette()
        {
            // Aviso de privacidade (LGPD) no primeiro uso.
            // A intenção é ser claro e dar ao usuário controle: se não aceitar, não abrimos a UI.
            if (!SisRuaSettings.IsPrivacyNoticeAccepted())
            {
                string settingsPath = SisRuaSettings.TryGetSettingsPathForDisplay();
                var answer = MessageBox.Show(
                    "O sisRUA utiliza serviços de mapa (OpenStreetMap) e telemetria básica para melhoria contínua.\n\n" +
                    "Ao continuar, você aceita que o plugin se comunique com o backend local e baixe dados geográficos.\n\n" +
                    "Deseja ativar o sisRUA?",
                    "Privacidade e Termos - sisRUA",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Information
                );

                if (answer != DialogResult.Yes)
                {
                    return;
                }

                SisRuaSettings.TryMarkPrivacyNoticeAccepted();
            }

            // --- Pre-flight Health Check ---
            // Verifica se o backend responde em até 2 segundos antes de tentar abrir o WebView2.
            // Isso evita que o usuário veja uma tela branca se o backend demorar para subir ou falhar.
            if (!SisRuaPlugin.EnsureBackendHealthy(TimeSpan.FromSeconds(2)))
            {
                MessageBox.Show(
                    "O backend do sisRUA ainda não está pronto ou falhou ao iniciar.\n\n" +
                    "Aguarde alguns segundos e tente novamente.\n" +
                    "Se o problema persistir, verifique o console do AutoCAD para mensagens de erro.",
                    "sisRUA - Backend Indisponível",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning
                );
                return;
            }

            if (_paletteSet == null)
            {
                _paletteSet = new PaletteSet("sisRUA", new Guid("FEA4C5F7-6834-4522-B968-440525C266E3"))
                {
                    Style = PaletteSetStyles.ShowPropertiesMenu | PaletteSetStyles.ShowAutoHideButton | PaletteSetStyles.ShowCloseButton,
                    MinimumSize = new System.Drawing.Size(450, 600),
                    Name = "sisRUA Interface"
                };

                var panel = new UserControl { Dock = DockStyle.Fill };
                _webView = new WebView2 { Dock = DockStyle.Fill, Visible = false }; // Começa invisível
                _uiInvokeTarget = panel;
                
                // --- Splash Screen Nativo ---
                _splashPanel = new Panel { 
                    Dock = DockStyle.Fill, 
                    BackColor = System.Drawing.Color.FromArgb(15, 23, 42), // Slate 900
                    Visible = true 
                };
                
                _splashLabel = new Label {
                    Text = _loadingMessages[0],
                    ForeColor = System.Drawing.Color.White,
                    Font = new System.Drawing.Font("Segoe UI", 10, System.Drawing.FontStyle.Bold),
                    TextAlign = System.Drawing.ContentAlignment.MiddleCenter,
                    Dock = DockStyle.Bottom,
                    Height = 100
                };

                var loaderIcon = new Label {
                    Text = "⌛", // Spinner simplificado
                    ForeColor = System.Drawing.Color.FromArgb(59, 130, 246), // Blue 500
                    Font = new System.Drawing.Font("Segoe UI", 24, System.Drawing.FontStyle.Bold),
                    TextAlign = System.Drawing.ContentAlignment.MiddleCenter,
                    Dock = DockStyle.Fill
                };

                _splashPanel.Controls.Add(loaderIcon);
                _splashPanel.Controls.Add(_splashLabel);

                // Timer para rotacionar mensagens
                _splashTimer = new System.Windows.Forms.Timer { Interval = 2500 };
                _splashTimer.Tick += (s, e) => {
                    _messageIndex = (_messageIndex + 1) % _loadingMessages.Length;
                    _splashLabel.Text = _loadingMessages[_messageIndex];
                };
                _splashTimer.Start();

                // Habilita o Drag & Drop no painel
                panel.AllowDrop = true;
                panel.DragEnter += Panel_DragEnter;
                panel.DragDrop += Panel_DragDrop;

                panel.Controls.Add(_webView);
                panel.Controls.Add(_splashPanel);
                _paletteSet.Add("WebView", panel);

                // A inicialização é assíncrona, então disparamos e não bloqueamos.
                InitializeWebViewAsync(); 

                // Monitora trocas de documento para atualizar georef
                Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.DocumentActivated += (s, e) => {
                    PushGeoLocationToUi();
                };
            }

            _paletteSet.Visible = true;
            PushGeoLocationToUi();
        }

        [CommandMethod("SISRUAESCALA", CommandFlags.Session)]
        public void SetSisRuaScale()
        {
            var doc = Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return;
            Editor ed = doc.Editor;
            if (ed == null) return;

            double? current = SisRuaSettings.TryReadMetersToUnits();

            var opts = new PromptDoubleOptions("\n[sisRUA] Informe o fator de escala (1 metro -> quantas unidades do desenho?)")
            {
                AllowNegative = false,
                AllowZero = false,
                AllowNone = true,
                DefaultValue = current ?? 1.0,
                UseDefaultValue = true
            };

            var res = ed.GetDouble(opts);
            if (res.Status != PromptStatus.OK && res.Status != PromptStatus.None)
            {
                return;
            }

            double v = (res.Status == PromptStatus.None) ? opts.DefaultValue : res.Value;
            if (double.IsNaN(v) || double.IsInfinity(v) || v <= 0.0)
            {
                ed.WriteMessage("\n[sisRUA] Valor inválido. Use um número > 0.");
                return;
            }

            if (!SisRuaSettings.TryWriteMetersToUnits(v))
            {
                ed.WriteMessage("\n[sisRUA] ERRO: não foi possível salvar settings.json em %LOCALAPPDATA%\\sisRUA.");
                return;
            }

            ed.WriteMessage($"\n[sisRUA] OK: escala salva. Agora 1m -> {v} unidades. Rode o SISRUA novamente para redesenhar.");
        }

        private void Panel_DragEnter(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                string[] files = (string[])e.Data.GetData(DataFormats.FileDrop);
                var allowedExtensions = new[] { ".json", ".geojson", ".kml", ".kmz" };
                if (files.Any(file => allowedExtensions.Contains(Path.GetExtension(file).ToLowerInvariant())))
                {
                    e.Effect = DragDropEffects.Copy;
                }
                else
                {
                    e.Effect = DragDropEffects.None;
                }
            }
            else
            {
                e.Effect = DragDropEffects.None;
            }
        }

        private void Panel_DragDrop(object sender, DragEventArgs e)
        {
            if (e.Data.GetDataPresent(DataFormats.FileDrop))
            {
                string[] files = (string[])e.Data.GetData(DataFormats.FileDrop);
                var allowedExtensions = new[] { ".json", ".geojson", ".kml", ".kmz" };
                
                string firstFile = files.FirstOrDefault(file => allowedExtensions.Contains(Path.GetExtension(file).ToLowerInvariant()));

                if (firstFile != null)
                {
                    try
                    {
                        string fileExtension = Path.GetExtension(firstFile).ToLowerInvariant();
                        string fileContent = null;
                        string fileName = Path.GetFileName(firstFile);

                        if (fileExtension == ".kmz")
                        {
                            string tempDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
                            try
                            {
                                fileContent = ExtractKmlFromKmz(firstFile, tempDir);
                                if (string.IsNullOrWhiteSpace(fileContent))
                                {
                                    throw new InvalidOperationException("Nenhum KML válido encontrado no arquivo KMZ.");
                                }
                                Debug.WriteLine($"[sisRUA] Arquivo KMZ '{fileName}' processado, KML extraído.");
                            }
                            finally
                            {
                                if (Directory.Exists(tempDir))
                                {
                                    Directory.Delete(tempDir, true); // Clean up temp directory
                                }
                            }
                        }
                        else
                        {
                            fileContent = File.ReadAllText(firstFile);
                        }
                        
                        if (_webView?.CoreWebView2 != null && !string.IsNullOrWhiteSpace(fileContent))
                        {
                            // Determine action based on original file type
                            string actionType = (fileExtension == ".kmz" || fileExtension == ".kml") ? "FILE_DROPPED_KML" : "FILE_DROPPED_GEOJSON";

                            PostUiMessage(new { action = actionType, data = new { fileName, content = fileContent } });
                            Debug.WriteLine($"[sisRUA] Arquivo '{fileName}' solto e enviado para a WebView como {actionType}.");
                        }
                    }
                    catch (System.Exception ex)
                    {
                        Debug.WriteLine($"[sisRUA] Erro ao ler o arquivo solto: {ex.Message}");
                        MessageBox.Show($"Erro ao processar o arquivo: {ex.Message}", "Erro de Leitura", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                }
            }
        }

        /// <summary>
        /// Extrai o conteúdo KML principal de um arquivo KMZ.
        /// </summary>
        /// <param name="kmzFilePath">Caminho completo para o arquivo KMZ.</param>
        /// <param name="tempExtractionDir">Diretório temporário para extração.</param>
        /// <returns>O conteúdo do arquivo KML principal como string.</returns>
        private static string ExtractKmlFromKmz(string kmzFilePath, string tempExtractionDir)
        {
            Directory.CreateDirectory(tempExtractionDir);
            ZipFile.ExtractToDirectory(kmzFilePath, tempExtractionDir);

            // Strategy for finding the main KML file:
            // 1. First, try to find "doc.kml" (standard KMZ convention)
            // 2. If not found, look for KML files in the root directory
            // 3. If still not found, search recursively for any .kml file
            // Note: For future improvement, consider parsing the main KML file to follow
            // NetworkLink elements that might point to other KML files within the archive,
            // ensuring all relevant geographic data is extracted.

            string kmlFilePath = null;

            // Priority 1: Look for "doc.kml" (standard KMZ root file)
            var allKmlFiles = Directory.GetFiles(tempExtractionDir, "*.kml", SearchOption.AllDirectories).ToList();
            kmlFilePath = allKmlFiles.FirstOrDefault(f => 
                Path.GetFileName(f).Equals("doc.kml", StringComparison.OrdinalIgnoreCase));

            // Priority 2: If not found, prefer KML files in the root directory
            if (kmlFilePath == null)
            {
                kmlFilePath = allKmlFiles.FirstOrDefault(f => 
                    Path.GetDirectoryName(f).Equals(tempExtractionDir, StringComparison.OrdinalIgnoreCase));
            }

            // Priority 3: Fallback to any KML file found
            if (kmlFilePath == null)
            {
                kmlFilePath = allKmlFiles.FirstOrDefault();
            }

            if (kmlFilePath == null)
            {
                throw new FileNotFoundException("Nenhum arquivo KML encontrado dentro do KMZ.");
            }

            return File.ReadAllText(kmlFilePath);
        }

        /// <summary>
        /// Tenta extrair a GEOGRAPHICLOCATION do AutoCAD e envia para o frontend.
        /// </summary>
        private static void PushGeoLocationToUi()
        {
            try
            {
                var doc = Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
                if (doc == null) return;

                /* GEOLOCATION TEMPORARILY DISABLED DUE TO BUILD ERROR
                var db = doc.Database;
                if (db.GeoLocationDataId == ObjectId.Null) return;

                using (var tr = db.TransactionManager.StartTransaction())
                {
                    var geo = tr.GetObject(db.GeoLocationDataId, OpenMode.ForRead) as GeoLocationData;
                    if (geo != null)
                    {
                        double lat = geo.Latitude;
                        double lon = geo.Longitude;

                        if (lat != 0 && lon != 0)
                        {
                            PostUiMessage(new { 
                                action = "GEOLOCATION_SYNC", 
                                data = new { latitude = lat, longitude = lon } 
                            });
                            Debug.WriteLine($"[sisRUA] Georeferenciamento detectado e enviado: {lat}, {lon}");
                        }
                    }
                    tr.Commit();
                }
                */
            }
            catch (System.Exception ex)
            {
                Debug.WriteLine($"[sisRUA] Erro ao extrair georef: {ex.Message}");
            }
        }

        private async void InitializeWebViewAsync()
        {
            try
            {
                // Em alguns ambientes (ex.: Civil 3D), a WebView2 pode falhar com E_ACCESSDENIED ao tentar
                // criar/usar o UserDataFolder padrão. Para evitar isso, forçamos um diretório gravável.
                string userDataFolder = GetWebViewUserDataFolder();
                if (_webView.CreationProperties == null)
                {
                    _webView.CreationProperties = new CoreWebView2CreationProperties();
                }
                _webView.CreationProperties.UserDataFolder = userDataFolder;

                // Garante que o ambiente da WebView2 (Core) está pronto.
                await _webView.EnsureCoreWebView2Async(null);
                
                // Configura a ponte de comunicação JS -> C#
                _webView.CoreWebView2.WebMessageReceived += CoreWebView2_WebMessageReceived;

                // --- Mitigação Prática: Auth Interception ---
                // Intercepta todas as chamadas para injetar o header de forma invisível.
                // Filtramos apenas para o domínio do backend para evitar vazamento de token para fora (ex: OSM).
                string backendHost = new Uri(SisRuaPlugin.BackendBaseUrl).Host;
                string filter = $"*://{backendHost}/*";
                _webView.CoreWebView2.AddWebResourceRequestedFilter(filter, CoreWebView2WebResourceContext.All);
                
                _webView.CoreWebView2.WebResourceRequested += (s, args) =>
                {
                    if (!string.IsNullOrWhiteSpace(SisRuaPlugin.BackendAuthToken))
                    {
                        args.Request.Headers.SetHeader(SisRuaPlugin.BackendAuthHeaderName, SisRuaPlugin.BackendAuthToken);
                    }
                };
                
                // Navega para a URL do frontend React.
                string baseUrl = SisRuaPlugin.BackendBaseUrl;
                if (string.IsNullOrWhiteSpace(baseUrl))
                {
                    Debug.WriteLine("[sisRUA] BackendBaseUrl vazio. Navegando para about:blank.");
                    baseUrl = "about:blank";
                }
                else
                {
                    // Em geral o plugin já aguardou o /health no Initialize(), mas aqui damos um "seguro" extra.
                    SisRuaPlugin.EnsureBackendHealthy(TimeSpan.FromSeconds(5));
                }
                _webView.Source = new Uri(baseUrl);
            }
            catch (System.Exception ex)
            {
                Debug.WriteLine($"[sisRUA] Falha ao inicializar a WebView2: {ex.Message}");
                MessageBox.Show(
                    $"Falha ao inicializar a interface web do sisRUA: {ex.Message}\n\n" +
                    $"Dica: verifique se o Microsoft Edge WebView2 Runtime está instalado e tente executar o Civil 3D sem modo Administrador.",
                    "Erro sisRUA",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
            }
        }

        private string GetWebViewUserDataFolder()
        {
            string localSisRuaDir = SisRuaPlugin.GetLocalSisRuaDir();
            if (string.IsNullOrEmpty(localSisRuaDir))
            {
                return Path.Combine(Path.GetTempPath(), "sisRUA_webview2");
            }
            return Path.Combine(localSisRuaDir, "webview2");
        }

        /// <summary>
        /// Manipula mensagens enviadas do frontend (JavaScript) via `window.chrome.webview.postMessage()`.
        /// Este é o ponto central da interoperabilidade entre o frontend e o plugin C#.
        /// </summary>
        private void CoreWebView2_WebMessageReceived(object sender, CoreWebView2WebMessageReceivedEventArgs args)
        {
            try
            {
                string jsonMessage = args.WebMessageAsJson;
                Debug.WriteLine($"[sisRUA] Mensagem recebida da WebView: {jsonMessage}");
                
                // Usamos JsonDocument para uma análise preliminar e eficiente da mensagem.
                using (JsonDocument doc = JsonDocument.Parse(jsonMessage))
                {
                    JsonElement root = doc.RootElement;
                    if (!root.TryGetProperty("action", out JsonElement actionElement))
                    {
                        Debug.WriteLine("[sisRUA] Mensagem da WebView ignorada: não contém a propriedade 'action'.");
                        return;
                    }

                    string action = actionElement.GetString()?.ToUpperInvariant();
                    if (string.IsNullOrWhiteSpace(action)) return;
                    
                    switch (action)
                    {
                        case "IMPORT_GEOJSON":
                            if (root.TryGetProperty("data", out JsonElement dataElement))
                            {
                                // O GeoJSON é recebido como uma string.
                                string geojsonData = dataElement.GetRawText();
                                
                                // IMPORTANTE: As APIs do AutoCAD só podem ser chamadas a partir da thread principal.
                                // O evento WebMessageReceived executa em uma thread de UI do WinForms, não na thread do AutoCAD.
                                // Usamos ExecuteInApplicationContext para delegar a execução do nosso comando para o contexto correto,
                                // garantindo a estabilidade e prevenindo "fatal errors".
                                // Usamos Task.Run para evitar warning CS4014 e permitir que a UI continue fluida.
                                _ = Task.Run(() => {
                                    Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.ExecuteInApplicationContext(
                                        (state) => { _ = SisRuaCommands.ImportarDadosCampo(geojsonData); }, null
                                    );
                                });
                            }
                            else
                            {
                                Debug.WriteLine("[sisRUA] Ação 'IMPORT_GEOJSON' recebida, mas sem a propriedade 'data'.");
                            }
                            break;

                        case "GENERATE_OSM":
                            if (root.TryGetProperty("data", out JsonElement osmDataElement))
                            {
                                // Extrai latitude, longitude e radius
                                double? lat = null, lon = null, radius = null;
                                if (osmDataElement.TryGetProperty("latitude", out JsonElement latElement))
                                    lat = latElement.GetDouble();
                                if (osmDataElement.TryGetProperty("longitude", out JsonElement lonElement))
                                    lon = lonElement.GetDouble();
                                if (osmDataElement.TryGetProperty("radius", out JsonElement radiusElement))
                                    radius = radiusElement.GetDouble();

                                if (lat.HasValue && lon.HasValue && radius.HasValue)
                                {
                                    _ = Task.Run(() => {
                                        Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.ExecuteInApplicationContext(
                                            (state) => { _ = SisRuaCommands.GerarProjetoOsm(lat.Value, lon.Value, radius.Value); }, null
                                        );
                                    });
                                }
                                else
                                {
                                    Debug.WriteLine("[sisRUA] Ação 'GENERATE_OSM' recebida, mas dados incompletos (lat/lon/radius).");
                                }
                            }
                            break;

                        case "APP_READY":
                            Debug.WriteLine("[sisRUA] Handshake recebido: React está pronto.");
                            if (_splashPanel != null && _webView != null)
                            {
                                _splashTimer?.Stop();
                                _splashPanel.Visible = false;
                                _webView.Visible = true;
                            }
                            break;

                        default:
                            Debug.WriteLine($"[sisRUA] Ação desconhecida recebida da WebView: {action}");
                            break;
                    }
                }
            }
            catch (JsonException jsonEx)
            {
                Debug.WriteLine($"[sisRUA] Erro de parsing no JSON recebido da WebView: {jsonEx.Message}");
            }
            catch (System.Exception ex)
            {
                Debug.WriteLine($"[sisRUA] Erro inesperado ao processar mensagem da WebView: {ex.Message}");
            }
        }
    }
}