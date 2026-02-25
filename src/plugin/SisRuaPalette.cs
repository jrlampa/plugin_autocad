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
        private static Control _uiInvokeTarget;
        private static readonly PaletteController _controller = new PaletteController();

        private static readonly string[] _loadingMessages = new[]
        {
            "Sintonizando o rádio do estagiário...",
            "Pedindo aumento pro Zaluar...",
            "Perguntando pro André algo cabuloso...",
            "Limpando o cache do AutoCAD...",
            "Calibrando o GPS de papel...",
            "Engraxando os eixos das ruas..."
        };

        public static void PostUiMessage(object message)
        {
            try
            {
                if (message == null) return;
                string json = JsonSerializer.Serialize(message);
                _uiInvokeTarget?.BeginInvoke((Action)(() => _webView?.CoreWebView2?.PostWebMessageAsString(json)));
            }
            catch { }
        }

        public static void NotifyAppReady()
        {
            if (_splashPanel != null && _webView != null)
            {
                _splashTimer?.Stop();
                _splashPanel.Visible = false;
                _webView.Visible = true;
            }
        }

        [CommandMethod("SISRUA", CommandFlags.Session)]
        public void ShowSisRuaPalette()
        {
            if (!SisRuaSettings.IsPrivacyNoticeAccepted())
            {
                if (MessageBox.Show("Deseja ativar o sisRUA?", "Privacidade", MessageBoxButtons.YesNo) != DialogResult.Yes) return;
                SisRuaSettings.TryMarkPrivacyNoticeAccepted();
            }

            if (!SisRuaPlugin.EnsureBackendHealthy(TimeSpan.FromSeconds(2)))
            {
                MessageBox.Show("Backend Indisponível.", "sisRUA", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            if (_paletteSet == null)
            {
                _paletteSet = new PaletteSet("sisRUA", new Guid("FEA4C5F7-6834-4522-B968-440525C266E3"))
                {
                    Style = PaletteSetStyles.ShowPropertiesMenu | PaletteSetStyles.ShowAutoHideButton | PaletteSetStyles.ShowCloseButton,
                    MinimumSize = new System.Drawing.Size(450, 600)
                };

                var panel = new UserControl { Dock = DockStyle.Fill, AllowDrop = true };
                _webView = new WebView2 { Dock = DockStyle.Fill, Visible = false };
                _uiInvokeTarget = panel;
                
                SetupSplashScreen(panel);

                panel.DragEnter += (s, e) => e.Effect = e.Data.GetDataPresent(DataFormats.FileDrop) ? DragDropEffects.Copy : DragDropEffects.None;
                panel.DragDrop += Panel_DragDrop;

                panel.Controls.Add(_webView);
                _paletteSet.Add("WebView", panel);

                InitializeWebViewAsync(); 
            }

            _paletteSet.Visible = true;
        }

        private void SetupSplashScreen(Control parent)
        {
            _splashPanel = new Panel { Dock = DockStyle.Fill, BackColor = System.Drawing.Color.FromArgb(15, 23, 42) };
            _splashLabel = new Label { Text = _loadingMessages[0], ForeColor = System.Drawing.Color.White, Dock = DockStyle.Bottom, TextAlign = System.Drawing.ContentAlignment.MiddleCenter, Height = 50 };
            _splashPanel.Controls.Add(_splashLabel);
            parent.Controls.Add(_splashPanel);

            _splashTimer = new System.Windows.Forms.Timer { Interval = 2000 };
            _splashTimer.Tick += (s, e) => {
                _messageIndex = (_messageIndex + 1) % _loadingMessages.Length;
                _splashLabel.Text = _loadingMessages[_messageIndex];
            };
            _splashTimer.Start();
        }

        private void Panel_DragDrop(object sender, DragEventArgs e)
        {
            string[] files = (string[])e.Data.GetData(DataFormats.FileDrop);
            string file = files.FirstOrDefault();
            if (file == null) return;

            try
            {
                string content = _controller.ProcessDroppedFile(file, out string action);
                PostUiMessage(new { action = action, data = new { fileName = Path.GetFileName(file), content = content } });
            }
            catch (Exception ex) { MessageBox.Show(ex.Message); }
        }

        private async void InitializeWebViewAsync()
        {
            try
            {
                _webView.CreationProperties = new CoreWebView2CreationProperties { UserDataFolder = Path.Combine(SisRuaPlugin.GetLocalSisRuaDir() ?? Path.GetTempPath(), "webview2") };
                await _webView.EnsureCoreWebView2Async(null);
                _webView.CoreWebView2.WebMessageReceived += (s, args) => _controller.HandleWebMessage(args.WebMessageAsJson);

                string filter = $"*://{new Uri(SisRuaPlugin.BackendBaseUrl).Host}/*";
                _webView.CoreWebView2.AddWebResourceRequestedFilter(filter, CoreWebView2WebResourceContext.All);
                _webView.CoreWebView2.WebResourceRequested += (s, args) =>
                {
                    if (!string.IsNullOrWhiteSpace(SisRuaPlugin.BackendAuthToken))
                        args.Request.Headers.SetHeader(SisRuaPlugin.BackendAuthHeaderName, SisRuaPlugin.BackendAuthToken);
                };

                _webView.Source = new Uri(SisRuaPlugin.BackendBaseUrl);
            }
            catch (Exception ex) { MessageBox.Show(ex.Message); }
        }

        [CommandMethod("SISRUAESCALA", CommandFlags.Session)]
        public void SetSisRuaScale()
        {
            var doc = Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
            var res = doc.Editor.GetDouble(new PromptDoubleOptions("\nEscala (1m -> X unidades):") { DefaultValue = SisRuaSettings.TryReadMetersToUnits() ?? 1.0 });
            if (res.Status == PromptStatus.OK) SisRuaSettings.TryWriteMetersToUnits(res.Value);
        }
    }
}
    }
}