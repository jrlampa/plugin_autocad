using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Text.Json;
using System.Threading.Tasks;

namespace sisRUA
{
    /// <summary>
    /// Contém os comandos do AutoCAD e a lógica de negócio para interagir com o desenho e o backend.
    /// </summary>
    public class SisRuaCommands
    {
        private static readonly HttpClient _httpClient = new HttpClient { Timeout = TimeSpan.FromMinutes(5) };
        private class BackendResponse { public string dxf_path { get; set; } }

        public static async Task ImportarDadosCampo(string geojsonData)
        {
            Editor ed = Application.DocumentManager.MdiActiveDocument.Editor;
            ed.WriteMessage("\n[sisRUA] Dados recebidos. Orquestrando importação...");

            string tempGeoJsonPath = "";
            try
            {
                tempGeoJsonPath = Path.Combine(Path.GetTempPath(), $"sisrua_{Guid.NewGuid()}.geojson");
                File.WriteAllText(tempGeoJsonPath, geojsonData);
                ed.WriteMessage($"\n[sisRUA] Dados de campo salvos em arquivo temporário: {tempGeoJsonPath}");

                ed.WriteMessage("\n[sisRUA] Enviando dados para o backend Python para processamento...");
                
                using (var formData = new MultipartFormDataContent())
                using (var fileStream = new FileStream(tempGeoJsonPath, FileMode.Open, FileAccess.Read))
                {
                    formData.Add(new StreamContent(fileStream), "geojson_file", Path.GetFileName(tempGeoJsonPath));

                    var response = await _httpClient.PostAsync("http://localhost:8000/process_field_data/", formData);
                    response.EnsureSuccessStatusCode();

                    string jsonResponse = await response.Content.ReadAsStringAsync();
                    var backendResponse = JsonSerializer.Deserialize<BackendResponse>(jsonResponse, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                    
                    string dxfPath = backendResponse?.dxf_path;

                    if (string.IsNullOrWhiteSpace(dxfPath) || !File.Exists(dxfPath))
                    {
                        throw new InvalidOperationException($"Backend processou com sucesso, mas o caminho do DXF retornado é inválido ou não existe: '{{dxfPath}}'");
                    }

                    ed.WriteMessage($"\n[sisRUA] Backend retornou o DXF gerado: {dxfPath}");
                    ImportDxf(dxfPath);
                }
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
                Debug.WriteLine($"[sisRUA] StackTrace: {ex.ToString()}");
            }
            finally
            {
                if (!string.IsNullOrEmpty(tempGeoJsonPath) && File.Exists(tempGeoJsonPath))
                {
                    try { File.Delete(tempGeoJsonPath); } 
                    catch (System.Exception) { /* Ignora falhas na limpeza */ }
                }
            }
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