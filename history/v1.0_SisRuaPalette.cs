using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Runtime;
using Autodesk.AutoCAD.Windows;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;
using System;
using System.Diagnostics;
using System.Text.Json;
using System.Windows.Forms;

namespace sisRUA
{
    /// <summary>
    /// Gerencia a PaletteSet (a janela flutuante) que hospeda a interface web (WebView2).
    /// </summary>
    public class SisRuaPalette
    {
        private static PaletteSet _paletteSet;
        private static WebView2 _webView;

        [CommandMethod("SISRUA", CommandFlags.Session)]
        public void ShowSisRuaPalette()
        {
            if (_paletteSet == null)
            {
                _paletteSet = new PaletteSet("sisRUA", new Guid("FEA4C5F7-6834-4522-B968-440525C266E3"))
                {
                    Style = PaletteSetStyles.ShowPropertiesMenu | PaletteSetStyles.ShowAutoHideButton | PaletteSetStyles.ShowCloseButton,
                    MinimumSize = new System.Drawing.Size(450, 600),
                    Name = "sisRUA Interface"
                };

                var panel = new UserControl { Dock = DockStyle.Fill };
                _webView = new WebView2 { Dock = DockStyle.Fill };
                
                panel.Controls.Add(_webView);
                _paletteSet.Add("WebView", panel);

                // A inicialização é assíncrona, então disparamos e não bloqueamos.
                InitializeWebViewAsync(); 
            }

            _paletteSet.Visible = true;
        }

        private async void InitializeWebViewAsync()
        {
            try
            {
                // Garante que o ambiente da WebView2 (Core) está pronto.
                await _webView.EnsureCoreWebView2Async(null);
                
                // Configura a ponte de comunicação JS -> C#
                _webView.CoreWebView2.WebMessageReceived += CoreWebView2_WebMessageReceived;
                
                // Navega para a URL do frontend React.
                _webView.Source = new Uri("http://localhost:8000");
            }
            catch (System.Exception ex)
            {
                Debug.WriteLine($"[sisRUA] Falha ao inicializar a WebView2: {ex.Message}");
                MessageBox.Show($"Falha ao inicializar a interface web do sisRUA: {ex.Message}", "Erro sisRUA", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
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
                                Application.DocumentManager.ExecuteInApplicationContext(
                                    (state) => { SisRuaCommands.ImportarDadosCampo(geojsonData); }, null
                                );
                            }
                            else
                            {
                                Debug.WriteLine("[sisRUA] Ação 'IMPORT_GEOJSON' recebida, mas sem a propriedade 'data'.");
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
