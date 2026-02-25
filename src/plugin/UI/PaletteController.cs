using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using System.Windows.Forms;
using Autodesk.AutoCAD.ApplicationServices;
using Microsoft.Web.WebView2.Core;

namespace sisRUA
{
    /// <summary>
    /// Controller for handling business logic and message routing for the SisRua Palette.
    /// SRP: Business logic and I/O (KMZ/GeoJSON) handling.
    /// </summary>
    public class PaletteController
    {
        public void HandleWebMessage(string jsonMessage)
        {
            try
            {
                using (JsonDocument doc = JsonDocument.Parse(jsonMessage))
                {
                    JsonElement root = doc.RootElement;
                    if (!root.TryGetProperty("action", out JsonElement actionElement)) return;

                    string action = actionElement.GetString()?.ToUpperInvariant();
                    if (string.IsNullOrWhiteSpace(action)) return;

                    switch (action)
                    {
                        case "IMPORT_GEOJSON":
                            if (root.TryGetProperty("data", out JsonElement dataElement))
                            {
                                string geojsonData = dataElement.GetRawText();
                                ExecuteInCadContext((state) => { _ = SisRuaCommands.ImportarDadosCampo(geojsonData); });
                            }
                            break;

                        case "GENERATE_OSM":
                            if (root.TryGetProperty("data", out JsonElement osmDataElement))
                            {
                                double? lat = GetDouble(osmDataElement, "latitude");
                                double? lon = GetDouble(osmDataElement, "longitude");
                                double? radius = GetDouble(osmDataElement, "radius");

                                if (lat.HasValue && lon.HasValue && radius.HasValue)
                                {
                                    ExecuteInCadContext((state) => { _ = SisRuaCommands.GerarProjetoOsm(lat.Value, lon.Value, radius.Value); });
                                }
                            }
                            break;

                        case "APP_READY":
                            SisRuaPalette.NotifyAppReady();
                            break;
                    }
                }
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[sisRUA] Controller Error: {ex.Message}");
            }
        }

        public string ProcessDroppedFile(string filePath, out string actionType)
        {
            actionType = "FILE_DROPPED_GEOJSON";
            string ext = Path.GetExtension(filePath).ToLowerInvariant();
            
            if (ext == ".kmz")
            {
                actionType = "FILE_DROPPED_KML";
                return ExtractKmlFromKmz(filePath);
            }
            
            if (ext == ".kml") actionType = "FILE_DROPPED_KML";
            return File.ReadAllText(filePath);
        }

        private string ExtractKmlFromKmz(string kmzPath)
        {
            string tempDir = Path.Combine(Path.GetTempPath(), Guid.NewGuid().ToString());
            try
            {
                Directory.CreateDirectory(tempDir);
                ZipFile.ExtractToDirectory(kmzPath, tempDir);
                
                var files = Directory.GetFiles(tempDir, "*.kml", SearchOption.AllDirectories);
                string kmlFile = files.FirstOrDefault(f => Path.GetFileName(f).Equals("doc.kml", StringComparison.OrdinalIgnoreCase)) ?? files.FirstOrDefault();
                
                if (kmlFile == null) throw new FileNotFoundException("KML not found in KMZ.");
                return File.ReadAllText(kmlFile);
            }
            finally
            {
                if (Directory.Exists(tempDir)) Directory.Delete(tempDir, true);
            }
        }

        private void ExecuteInCadContext(Action<object> action)
        {
            _ = Task.Run(() => {
                Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.ExecuteInApplicationContext(
                    new Action<object>(action), null
                );
            });
        }

        private double? GetDouble(JsonElement element, string propName)
        {
            if (element.TryGetProperty(propName, out JsonElement p)) return p.GetDouble();
            return null;
        }
    }
}
