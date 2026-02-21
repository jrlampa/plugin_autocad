// Commands/SisRuaCadUtils.cs
// Utilitários CAD de baixo nível: blocos, layers, escalas, cores, HTTP autenticado.
// Isolados de SisRuaCommands.cs para respeitar o limite de 500 linhas por arquivo (SoC).
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using System;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace sisRUA
{
    using sisRUA.UI;
    using Exception = System.Exception;

    public partial class SisRuaCommands
    {
        // ──────────────────────────────────────────────────────────────────────────
        // Bloco CAD: carregamento e inserção
        // ──────────────────────────────────────────────────────────────────────────

        private static ObjectId EnsureBlockDefinitionLoaded(
            Transaction tr, Database db, string blockName, string blockFilePath)
        {
            SisRuaLog.WriteDebugLine(
                "SisRuaCommands:EnsureBlockDefinitionLoaded", "entry",
                new { blockName, blockFilePath, fileExists = File.Exists(blockFilePath ?? "") },
                "H1", "run1");

            Log($"INFO: Ensuring block definition '{blockName}' from '{blockFilePath}' is loaded.");
            BlockTable bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);

            if (bt.Has(blockName))
            {
                Log($"DEBUG: Block '{blockName}' already loaded.");
                return bt[blockName];
            }

            Log($"INFO: Block '{blockName}' not found. Loading from file '{blockFilePath}'.");
            using (Database blockDb = new Database(false, true))
            {
                try
                {
                    blockDb.ReadDwgFile(blockFilePath, FileShare.Read, true, "");
                }
                catch (Exception ex)
                {
                    Log($"ERROR: Failed to read block file '{blockFilePath}' as DWG: {ex.Message}");
                    try
                    {
                        blockDb.DxfIn(blockFilePath, "");
                    }
                    catch (Exception dxfEx)
                    {
                        Log($"ERROR: Failed to read block file '{blockFilePath}' as DXF: {dxfEx.Message}");
                        throw new Exception(
                            $"Não foi possível carregar a definição do bloco '{blockName}' " +
                            $"do arquivo '{blockFilePath}'. Erro: {dxfEx.Message}", dxfEx);
                    }
                }

                var ids = new ObjectIdCollection();
                using (Transaction blockTr = blockDb.TransactionManager.StartTransaction())
                {
                    BlockTable blockFileBt =
                        (BlockTable)blockTr.GetObject(blockDb.BlockTableId, OpenMode.ForRead);
                    foreach (ObjectId btrId in blockFileBt)
                    {
                        BlockTableRecord btr =
                            (BlockTableRecord)blockTr.GetObject(btrId, OpenMode.ForRead);
                        if (btr.IsAnonymous || btr.IsLayout) continue;
                        if (string.Equals(btr.Name, blockName, StringComparison.OrdinalIgnoreCase) ||
                            btr.Name == "*Model_Space")
                        {
                            ids.Add(btrId);
                        }
                    }
                    blockTr.Commit();
                }

                if (ids.Count == 0)
                    throw new Exception(
                        $"Não foi encontrada a definição do bloco '{blockName}' " +
                        $"dentro do arquivo '{blockFilePath}'.");

                bt.UpgradeOpen();
                db.Insert(blockName, blockDb, true);
                bt.DowngradeOpen();
                Log($"INFO: Block definition '{blockName}' loaded successfully.");
                return bt[blockName];
            }
        }

        private static void InsertBlock(
            Transaction tr, Database db, BlockTableRecord ms,
            string blockName, string blockFilePath,
            Autodesk.AutoCAD.Geometry.Point3d insertionPoint,
            double rotation, double scale, string layerName, string colorStr = null)
        {
            Log($"INFO: Inserting block '{blockName}' at {insertionPoint.X},{insertionPoint.Y},{insertionPoint.Z}.");
            try
            {
                ObjectId blockDefId = EnsureBlockDefinitionLoaded(tr, db, blockName, blockFilePath);

                BlockReference br = new BlockReference(insertionPoint, blockDefId)
                {
                    Rotation = rotation,
                    ScaleFactors = new Autodesk.AutoCAD.Geometry.Scale3d(scale),
                    Layer = layerName,
                    Color = !string.IsNullOrWhiteSpace(colorStr)
                        ? ParseColor(colorStr)
                        : Color.FromColorIndex(ColorMethod.ByLayer, 256),
                };

                ms.AppendEntity(br);
                tr.AddNewlyCreatedDBObject(br, true);
                Log($"DEBUG: Block instance '{blockName}' inserted successfully.");
            }
            catch (Exception ex)
            {
                Log($"ERROR: Failed to insert block '{blockName}': {ex.Message}");
            }
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Log delegado (encaminha para SisRuaLog com nível correto)
        // ──────────────────────────────────────────────────────────────────────────

        public static void Log(string message)
        {
            if (message.StartsWith("ERROR")) SisRuaLog.Error(message.Replace("ERROR: ", ""));
            else if (message.StartsWith("WARN")) SisRuaLog.Warn(message.Replace("WARN: ", ""));
            else SisRuaLog.Info(message);
        }

        // ──────────────────────────────────────────────────────────────────────────
        // HTTP helpers autenticados
        // ──────────────────────────────────────────────────────────────────────────

        private static string GetBackendBaseUrlOrAlert(Editor ed)
        {
            string baseUrl = SisRuaPlugin.BackendBaseUrl;
            if (string.IsNullOrWhiteSpace(baseUrl))
            {
                ed?.WriteMessage(
                    "\n[sisRUA] ERRO: BackendBaseUrl não definido. O plugin inicializou corretamente?");
                Application.ShowAlertDialog(
                    "Backend do sisRUA não foi inicializado corretamente.\n" +
                    "Feche e reabra o AutoCAD e execute o comando SISRUA novamente.");
                Log("ERROR: BackendBaseUrl not defined.");
                return null;
            }

            SisRuaPlugin.EnsureBackendHealthy(TimeSpan.FromSeconds(10));
            return baseUrl;
        }

        private static HttpRequestMessage CreateAuthedJsonRequest(
            HttpMethod method, string url, string jsonBody)
        {
            var req = new HttpRequestMessage(method, url);
            if (!string.IsNullOrWhiteSpace(SisRuaPlugin.BackendAuthToken))
                req.Headers.TryAddWithoutValidation(
                    SisRuaPlugin.BackendAuthHeaderName, SisRuaPlugin.BackendAuthToken);

            if (jsonBody != null)
                req.Content = new StringContent(jsonBody, Encoding.UTF8, "application/json");

            return req;
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Notificação de progresso de job para a UI (WebView2)
        // ──────────────────────────────────────────────────────────────────────────

        private static void NotifyUiJob(JobStatusResponse job)
        {
            try
            {
                SisRuaPalette.PostUiMessage(new { action = "JOB_PROGRESS", data = job });
            }
            catch (Exception ex)
            {
                Log($"WARN: Failed to notify UI of job progress: {ex.Message}");
            }
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Job assíncrono: criação e polling até completion/failure/timeout
        // ──────────────────────────────────────────────────────────────────────────

        private static async Task<PrepareResponse> RunPrepareJobAsync(
            Editor ed, string baseUrl, PrepareJobRequest payload, ProcessingDialog dlg)
        {
            Log($"INFO: Running prepare job for kind: {payload.Kind}");
            string createJson = JsonSerializer.Serialize(payload, _jsonOptions);

            using (var createReq = CreateAuthedJsonRequest(
                HttpMethod.Post, $"{baseUrl}/api/v1/jobs/prepare", createJson))
            {
                var createResp = await _httpClient.SendAsync(createReq);
                createResp.EnsureSuccessStatusCode();
                string createText = await createResp.Content.ReadAsStringAsync();
                var job = JsonSerializer.Deserialize<JobStatusResponse>(createText, _jsonOptions);

                if (job == null || string.IsNullOrWhiteSpace(job.JobId))
                    throw new InvalidOperationException(
                        "Backend retornou resposta inválida ao criar job.");

                NotifyUiJob(job);

                var sw = Stopwatch.StartNew();
                double lastProgress = -1;
                string lastMessage = null;
                string lastStatus = null;

                while (sw.Elapsed < TimeSpan.FromMinutes(10))
                {
                    if (dlg != null && dlg.WasCancelled)
                    {
                        Log($"INFO: Cancellation requested by user for job {job.JobId}.");
                        using (var cancelReq = CreateAuthedJsonRequest(
                            HttpMethod.Delete, $"{baseUrl}/api/v1/jobs/{job.JobId}", null))
                        {
                            await _httpClient.SendAsync(cancelReq);
                        }
                        throw new OperationCanceledException("Cancelado pelo usuário.");
                    }

                    using (var pollReq = CreateAuthedJsonRequest(
                        HttpMethod.Get, $"{baseUrl}/api/v1/jobs/{job.JobId}", jsonBody: null))
                    {
                        var pollResp = await _httpClient.SendAsync(pollReq);
                        pollResp.EnsureSuccessStatusCode();
                        string pollText = await pollResp.Content.ReadAsStringAsync();
                        job = JsonSerializer.Deserialize<JobStatusResponse>(pollText, _jsonOptions);

                        if (job == null)
                            throw new InvalidOperationException(
                                "Backend retornou resposta inválida no polling do job.");

                        bool changed =
                            !string.Equals(lastStatus, job.Status, StringComparison.OrdinalIgnoreCase) ||
                            Math.Abs(lastProgress - job.Progress) > 0.0001 ||
                            !string.Equals(lastMessage, job.Message, StringComparison.Ordinal);

                        if (changed)
                        {
                            lastStatus = job.Status;
                            lastProgress = job.Progress;
                            lastMessage = job.Message;
                            ed?.WriteMessage(
                                $"\n[sisRUA] Job {job.JobId}: {job.Status} {job.Progress:P0} - {job.Message}");
                            NotifyUiJob(job);
                        }

                        if (string.Equals(job.Status, "completed", StringComparison.OrdinalIgnoreCase))
                        {
                            if (job.Result.ValueKind == JsonValueKind.Undefined ||
                                job.Result.ValueKind == JsonValueKind.Null)
                                throw new InvalidOperationException("Job concluído sem result.");

                            var result = job.Result.Deserialize<PrepareResponse>(_jsonOptions);
                            Log($"INFO: Job {job.JobId} completed successfully.");
                            return result;
                        }

                        if (string.Equals(job.Status, "failed", StringComparison.OrdinalIgnoreCase))
                        {
                            Log($"ERROR: Job {job.JobId} failed. Error: {job.Error ?? job.Message}");
                            if (job.Error == "CANCELLED")
                                throw new OperationCanceledException(
                                    "Job cancelado pelo usuário no backend.");
                            throw new InvalidOperationException(
                                job.Error ?? job.Message ?? "Job falhou no backend.");
                        }
                    }

                    await Task.Delay(500);
                }

                Log($"ERROR: Job {job.JobId} timed out after {sw.Elapsed.TotalMinutes:F1} min " +
                    $"(limite: 10 min).");
                throw new TimeoutException(
                    "Tempo limite excedido (10 min) aguardando job do backend.");
            }
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Escala metros → unidades do desenho (INSUNITS do DWG)
        // ──────────────────────────────────────────────────────────────────────────

        private static double GetMetersToDrawingUnitsScale(Database db)
        {
            try
            {
                string overrideScale = Environment.GetEnvironmentVariable("SISRUA_M_TO_UNITS");
                if (!string.IsNullOrWhiteSpace(overrideScale))
                {
                    overrideScale = overrideScale.Trim().Replace(',', '.');
                    if (double.TryParse(overrideScale, NumberStyles.Float,
                        CultureInfo.InvariantCulture, out double forced) &&
                        forced > 0.0 && IsFinite(forced))
                    {
                        return forced;
                    }
                }

                double? persisted = SisRuaSettings.TryReadMetersToUnits();
                if (persisted.HasValue) return persisted.Value;

                object v = Application.GetSystemVariable("INSUNITS");
                int insunits = 0;
                if (v is short s) insunits = s;
                else if (v is int i) insunits = i;
                else if (v != null) int.TryParse(v.ToString(), out insunits);

                switch (insunits)
                {
                    case 0:
                        try
                        {
                            object m = Application.GetSystemVariable("MEASUREMENT");
                            int measurement = 0;
                            if (m is short ms) measurement = ms;
                            else if (m is int mi) measurement = mi;
                            else if (m != null) int.TryParse(m.ToString(), out measurement);
                            return measurement == 1 ? 1.0 : 39.37007874015748;
                        }
                        catch (Exception ex)
                        {
                            Log($"WARN: Error determining MEASUREMENT: {ex.Message}");
                            return 1.0;
                        }
                    case 1:  return 39.37007874015748; // inches
                    case 2:  return 3.280839895013123; // feet
                    case 3:  return 0.0006213711922373339; // miles
                    case 4:  return 1000.0; // millimeters
                    case 5:  return 100.0;  // centimeters
                    case 6:  return 1.0;    // meters
                    case 7:  return 0.001;  // kilometers
                    default: return 1.0;
                }
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in GetMetersToDrawingUnitsScale: {ex.Message}");
            }
            return 1.0;
        }

        private static bool IsFinite(double x) =>
            !(double.IsNaN(x) || double.IsInfinity(x));

        // ──────────────────────────────────────────────────────────────────────────
        // Cor CAD: parse de ACI ou RGB
        // ──────────────────────────────────────────────────────────────────────────

        private static Color ParseColor(string colorStr)
        {
            if (string.IsNullOrWhiteSpace(colorStr))
                return Color.FromColorIndex(ColorMethod.ByLayer, 256);
            try
            {
                if (short.TryParse(colorStr, out short aci))
                    return Color.FromColorIndex(ColorMethod.ByAci, aci);

                var parts = colorStr.Split(',');
                if (parts.Length == 3 &&
                    byte.TryParse(parts[0], out byte r) &&
                    byte.TryParse(parts[1], out byte g) &&
                    byte.TryParse(parts[2], out byte b))
                {
                    return Color.FromRgb(r, g, b);
                }
            }
            catch { }
            return Color.FromColorIndex(ColorMethod.ByLayer, 256);
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Layer: garante existência com ACI opcional
        // ──────────────────────────────────────────────────────────────────────────

        private static void EnsureLayer(
            Transaction tr, Database db, LayerTable lt, string layerName, short? aci = null)
        {
            if (lt.Has(layerName)) return;
            try
            {
                lt.UpgradeOpen();
                var ltr = new LayerTableRecord { Name = layerName };
                if (aci.HasValue)
                    ltr.Color = Color.FromColorIndex(ColorMethod.ByAci, aci.Value);
                lt.Add(ltr);
                tr.AddNewlyCreatedDBObject(ltr, true);
                Log($"INFO: Created new layer: {layerName}");
            }
            catch (Exception ex)
            {
                Log($"ERROR: Failed to create layer {layerName}: {ex.Message}");
            }
        }
    }
}
