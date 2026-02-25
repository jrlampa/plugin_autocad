// Commands/SisRuaDrawHelpers.cs
// Lógica de desenho CAD: DrawCadFeatureDtos, metadados BIM-LITE, atribuição OSM.
// Isolado de SisRuaCommands.cs para respeitar o limite de 500 linhas por arquivo (SoC).
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.DatabaseServices;
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;

namespace sisRUA
{
    using sisRUA.Core.DTOs;
    using sisRUA.UI;
    using Exception = System.Exception;

    public partial class SisRuaCommands
    {
        // ──────────────────────────────────────────────────────────────────────────
        // Desenho em streaming por chunks (resposta a cancelamento + UX fluída)
        // ──────────────────────────────────────────────────────────────────────────

        private static async Task DrawCadFeatureDtos(
            IEnumerable<CadFeatureDto> features, ProcessingDialog dlg)
        {
            SisRuaLog.WriteDebugLine(
                "SisRuaCommands:DrawCadFeatureDtos", "entry",
                new { featureCount = features?.Count() ?? 0 }, "H5", "run1");

            Log("INFO: DrawCadFeatureDtos started.");
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null)
            {
                Log("WARN: DocumentManager.MdiActiveDocument is null in DrawCadFeatureDtos.");
                return;
            }

            Database db = doc.Database;
            var ed = doc.Editor;
            double metersToDrawingUnits = GetMetersToDrawingUnitsScale(db);

            ed.WriteMessage("\n[sisRUA] Processando geometria em background (interface liberada)...");

            // ── Phase 2: pré-processamento em background ──────────────────────────
            object processingResultRaw = null;
            try
            {
                var task = Task.Run(async () =>
                {
                    try
                    {
                        int inputCount = features.Count();
                        if (dlg.WasCancelled) return null;

                        // Backend já entrega geometria limpa — Thin Client (BIM-LITE / SaaS)
                        var finalFeatures = features.ToList();
                        dlg.SetProgress(75);

                        return new
                        {
                            Features = finalFeatures,
                            OriginalCount = inputCount,
                            FinalCount = finalFeatures.Count,
                            DuplicatesRemoved = 0, // tratado no backend
                            MergedCount = 0,       // tratado no backend
                            Tolerance = 0.0,       // tratado no backend
                        };
                    }
                    catch (Exception ex)
                    {
                        Log($"ERROR: Background processing failed: {ex.Message}");
                        TelemetryService.ReportErrorSync("BACKGROUND_PROCESSING", ex);
                        throw;
                    }
                }, dlg.CancellationToken);

                while (!task.IsCompleted)
                {
                    if (dlg.WasCancelled)
                    {
                        ed.WriteMessage("\n[sisRUA] Operação cancelada pelo usuário.");
                        return;
                    }
                    await Task.Delay(100);
                }

                processingResultRaw = await task;
            }
            finally
            {
                // dlg é descartado pelo using() do chamador
            }

            if (processingResultRaw == null) return; // cancelado

            dynamic processingResult = processingResultRaw;
            IEnumerable<CadFeatureDto> finalFeaturesList =
                (IEnumerable<CadFeatureDto>)processingResult.Features;
            int duplicatesRemoved = (int)processingResult.DuplicatesRemoved;
            int mergedCount = (int)processingResult.MergedCount;
            double finalTolerance = (double)processingResult.Tolerance;

            Log("INFO: Background processing finished. Drawing entities...");

            if (duplicatesRemoved > 0)
                ed.WriteMessage($"\n[sisRUA] Aviso: {duplicatesRemoved} polylines duplicadas removidas.");
            if (mergedCount > 0)
                ed.WriteMessage($"\n[sisRUA] Aviso: {mergedCount} polylines foram fundidas.");
            if (finalTolerance > 0)
                ed.WriteMessage(
                    $"\n[sisRUA] Aviso: Polylines simplificadas (tolerância: {finalTolerance:F2} un.).");

            // ── Phase 3: desenho em chunks (chunked transaction streaming) ─────────
            if (doc.IsDisposed) return;

            int createdPolylines = 0;
            int createdBlocks = 0;
            const int chunkSize = 50;
            var featureList = finalFeaturesList.ToList();

            for (int i = 0; i < featureList.Count; i += chunkSize)
            {
                if (dlg.WasCancelled) break;

                var chunk = featureList.Skip(i).Take(chunkSize);

                SisRuaTransactionalShield.Execute((d, database, tr) =>
                {
                    LayerTable lt =
                        (LayerTable)tr.GetObject(database.LayerTableId, OpenMode.ForRead);
                    BlockTable bt =
                        (BlockTable)tr.GetObject(database.BlockTableId, OpenMode.ForRead);
                    BlockTableRecord ms =
                        (BlockTableRecord)tr.GetObject(
                            bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                    // Extrai origem (SIRGAS 2000 offset) da primeira feature com propriedade sys_sisrua_origin
                    double originX = 0, originY = 0;
                    var firstWithOrigin = featureList.FirstOrDefault(f =>
                        f.OriginalGeoJsonProperties != null &&
                        f.OriginalGeoJsonProperties.ContainsKey("sys_sisrua_origin"));
                    if (firstWithOrigin != null)
                    {
                        try
                        {
                            var el = (JsonElement?)firstWithOrigin
                                .OriginalGeoJsonProperties["sys_sisrua_origin"];
                            if (el.HasValue &&
                                el.Value.ValueKind == JsonValueKind.Array)
                            {
                                originX = el.Value[0].GetDouble();
                                originY = el.Value[1].GetDouble();
                            }
                        }
                        catch { }
                    }

                    foreach (var f in chunk)
                    {
                        if (f == null) continue;
                        var (layerName, aci) = GetLayerStyleForFeature(f);
                        EnsureLayer(tr, database, lt, layerName, aci);

                        switch (f.FeatureType)
                        {
                            case CadFeatureDtoType.Polyline:
                                if (f.CoordsXy == null || f.CoordsXy.Count < 2) continue;
                                var pts = f.CoordsXy.Select(pt => new SisRuaPoint(
                                    (pt[0] + originX) * metersToDrawingUnits,
                                    (pt[1] + originY) * metersToDrawingUnits,
                                    f.Elevation.HasValue
                                        ? f.Elevation.Value * metersToDrawingUnits
                                        : 0.0
                                )).ToList();

                                // Cria a polilinha de eixo diretamente na transação corrente
                                // para que possamos gerar as bordas de meio-fio no mesmo contexto.
                                var centerPline = sisRUA.Engine.CadFeatureFactory.CreatePolyline(pts, false);
                                centerPline.Layer = layerName;
                                if (f.Elevation.HasValue)
                                    centerPline.Elevation = f.Elevation.Value * metersToDrawingUnits;
                                if (!string.IsNullOrWhiteSpace(f.Color))
                                    centerPline.Color = ParseColor(f.Color);
                                ms.AppendEntity(centerPline);
                                tr.AddNewlyCreatedDBObject(centerPline, true);
                                var centerMeta = ExtractMetadata(f);
                                if (centerMeta.Count > 0)
                                    sisRUA.Engine.CadFeatureFactory.AttachMetadata(centerPline, centerMeta, tr);
                                createdPolylines++;

                                // MEIO-FIO: gera as bordas laterais ("de meio-fio a meio-fio").
                                // Aplicado a vias (highway) com largura de via definida.
                                double? widthUnits = TryGetRoadWidthUnits(f, metersToDrawingUnits);
                                if (!string.IsNullOrWhiteSpace(f.Highway) &&
                                    widthUnits.HasValue && widthUnits.Value > 0.05)
                                {
                                    const string meiofioLayer = "SISRUA_MEIO_FIO";
                                    EnsureLayer(tr, database, lt, meiofioLayer, aci: 4); // ACI 4 = Cyan
                                    TryAppendOffsetRoadEdges(tr, ms, centerPline,
                                        widthUnits.Value / 2.0, meiofioLayer);
                                }
                                break;

                            case CadFeatureDtoType.Point:
                                if (f.InsertionPointXy == null || f.InsertionPointXy.Count < 2 ||
                                    string.IsNullOrWhiteSpace(f.BlockName) ||
                                    string.IsNullOrWhiteSpace(f.BlockFilePath)) continue;
                                var insPt = new SisRuaPoint(
                                    (f.InsertionPointXy[0] + originX) * metersToDrawingUnits,
                                    (f.InsertionPointXy[1] + originY) * metersToDrawingUnits,
                                    f.Elevation.HasValue
                                        ? f.Elevation.Value * metersToDrawingUnits
                                        : 0.0);
                                Engine.InsertBlock(
                                    f.BlockName, insPt,
                                    f.Rotation ?? 0.0, f.Scale ?? 1.0,
                                    layerName, ExtractMetadata(f));
                                createdBlocks++;
                                break;
                        }
                    }
                });

                ed.UpdateScreen();
                dlg.SetProgress(75 + (int)(25.0 * i / featureList.Count));
                await Task.Delay(5);
            }

            ed.WriteMessage(
                $"\n[sisRUA] Sucesso! {createdPolylines} polylines e {createdBlocks} blocos criados.");

            EnsurePadrãoSisRuaMetadata(db);
            ed.Regen();
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Metadados BIM-LITE: extração de propriedades para XData
        // ──────────────────────────────────────────────────────────────────────────

        private static Dictionary<string, string> ExtractMetadata(CadFeatureDto f)
        {
            var meta = new Dictionary<string, string>();
            if (!string.IsNullOrEmpty(f.Name)) meta["name"] = f.Name;
            if (!string.IsNullOrEmpty(f.Highway)) meta["highway"] = f.Highway;
            if (f.WidthMeters.HasValue)
                meta["width_m"] = f.WidthMeters.Value.ToString(CultureInfo.InvariantCulture);

            if (f.OriginalGeoJsonProperties != null)
            {
                foreach (var kvp in f.OriginalGeoJsonProperties)
                {
                    if (kvp.Value is JsonElement je)
                    {
                        if (je.ValueKind == JsonValueKind.String ||
                            je.ValueKind == JsonValueKind.Number ||
                            je.ValueKind == JsonValueKind.True ||
                            je.ValueKind == JsonValueKind.False)
                        {
                            meta[kvp.Key] = je.ToString();
                        }
                    }
                    else if (kvp.Value != null)
                    {
                        meta[kvp.Key] = kvp.Value.ToString();
                    }
                }
            }
            return meta;
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Auditoria: injeta dicionário de metadados sisRUA no DWG (ISO 9001)
        // ──────────────────────────────────────────────────────────────────────────

        private static void EnsurePadrãoSisRuaMetadata(Database db)
        {
            try
            {
                using (var tr = db.TransactionManager.StartTransaction())
                {
                    var nod = (DBDictionary)tr.GetObject(
                        db.NamedObjectsDictionaryId, OpenMode.ForWrite);

                    if (!nod.Contains("SISRUA_METADATA"))
                    {
                        var sisruaDict = new DBDictionary();
                        nod.SetAt("SISRUA_METADATA", sisruaDict);
                        tr.AddNewlyCreatedDBObject(sisruaDict, true);

                        var xRec = new Xrecord
                        {
                            Data = new ResultBuffer(
                                new TypedValue((int)DxfCode.Text, Guid.NewGuid().ToString()),
                                new TypedValue(
                                    (int)DxfCode.Text,
                                    DateTime.UtcNow.ToString("yyyy-MM-dd HH:mm:ss")),
                                new TypedValue(
                                    (int)DxfCode.Text,
                                    $"Padrão sisRUA v{System.Reflection.Assembly.GetExecutingAssembly().GetName().Version?.ToString(3) ?? "0.1.0"}"))
                        };

                        sisruaDict.SetAt("Audit_ID", xRec);
                        tr.AddNewlyCreatedDBObject(xRec, true);
                    }
                    tr.Commit();
                }
            }
            catch (Exception ex)
            {
                Log($"ERROR: Failed to inject Audit Metadata: {ex.Message}");
            }
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Atribuição OSM (ODbL): insere MText de copyright no DWG
        // ──────────────────────────────────────────────────────────────────────────

        private static void EnsureOsmAttributionMText(IEnumerable<CadFeatureDto> features)
        {
            try
            {
                Document doc = Application.DocumentManager.MdiActiveDocument;
                if (doc == null) return;

                Database db = doc.Database;
                double mtu = GetMetersToDrawingUnitsScale(db);

                double minX = double.PositiveInfinity, minY = double.PositiveInfinity;
                double maxX = double.NegativeInfinity, maxY = double.NegativeInfinity;

                if (features != null)
                {
                    foreach (var f in features)
                    {
                        if (f?.CoordsXy == null) continue;
                        foreach (var pt in f.CoordsXy)
                        {
                            if (pt == null || pt.Count < 2) continue;
                            double x = pt[0] * mtu, y = pt[1] * mtu;
                            if (!IsFinite(x) || !IsFinite(y)) continue;
                            if (x < minX) minX = x;
                            if (y < minY) minY = y;
                            if (x > maxX) maxX = x;
                            if (y > maxY) maxY = y;
                        }
                    }
                }

                if (!IsFinite(minX) || !IsFinite(minY) || !IsFinite(maxX) || !IsFinite(maxY))
                    return;

                double span = Math.Max(maxX - minX, maxY - minY);
                double textHeight = span > 0 ? span / 500.0 : 10.0 * mtu;
                textHeight = Math.Max(2.0 * mtu, Math.Min(50.0 * mtu, textHeight));

                var insPt = new Autodesk.AutoCAD.Geometry.Point3d(
                    minX + textHeight, maxY - textHeight, 0);

                using (doc.LockDocument())
                using (Transaction tr = db.TransactionManager.StartTransaction())
                {
                    LayerTable lt =
                        (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
                    const string layerName = "SISRUA_ATTRIB";
                    EnsureLayer(tr, db, lt, layerName, aci: 7);

                    ObjectId msId = SymbolUtilityServices.GetBlockModelSpaceId(db);
                    BlockTableRecord ms =
                        (BlockTableRecord)tr.GetObject(msId, OpenMode.ForRead);

                    foreach (ObjectId id in ms)
                    {
                        if (tr.GetObject(id, OpenMode.ForRead) is MText mt)
                        {
                            if ((mt.Contents ?? string.Empty).IndexOf(
                                "OpenStreetMap contributors",
                                StringComparison.OrdinalIgnoreCase) >= 0)
                                return;
                        }
                    }

                    ms.UpgradeOpen();
                    var mtext = new MText
                    {
                        Layer = layerName,
                        Color = Color.FromColorIndex(ColorMethod.ByLayer, 256),
                        Location = insPt,
                        TextHeight = textHeight,
                        Contents = "© OpenStreetMap contributors\\P" +
                                   "https://www.openstreetmap.org/copyright",
                    };
                    ms.AppendEntity(mtext);
                    tr.AddNewlyCreatedDBObject(mtext, true);
                    tr.Commit();
                }
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in EnsureOsmAttributionMText: {ex.Message}");
            }
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Largura de via (estimativa em unidades do desenho)
        // ──────────────────────────────────────────────────────────────────────────

        private static double? TryGetRoadWidthUnits(CadFeatureDto f, double mtu)
        {
            try
            {
                if (f != null && f.WidthMeters.HasValue &&
                    f.WidthMeters.Value > 0.01 && IsFinite(f.WidthMeters.Value))
                    return f.WidthMeters.Value * mtu;

                double? wMeters = null;
                switch (f?.Highway?.Trim()?.ToLowerInvariant())
                {
                    case "motorway":     wMeters = 20.0; break;
                    case "trunk":        wMeters = 16.0; break;
                    case "primary":      wMeters = 12.0; break;
                    case "secondary":    wMeters = 10.0; break;
                    case "tertiary":     wMeters =  9.0; break;
                    case "residential":  wMeters =  7.0; break;
                    case "unclassified": wMeters =  7.0; break;
                    case "living_street":wMeters =  6.0; break;
                    case "service":      wMeters =  5.0; break;
                    case "footway":
                    case "path":
                    case "cycleway":     wMeters =  2.5; break;
                }
                return wMeters.HasValue ? (double?)(wMeters.Value * mtu) : null;
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in TryGetRoadWidthUnits: {ex.Message}");
                return null;
            }
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Bordas de via (offset bilateral para largura real)
        // ──────────────────────────────────────────────────────────────────────────

        private static bool TryAppendOffsetRoadEdges(
            Transaction tr, BlockTableRecord ms,
            Polyline center, double halfWidthUnits, string layerName)
        {
            try
            {
                if (center == null)
                {
                    Log("WARN: TryAppendOffsetRoadEdges received null center polyline.");
                    return false;
                }
                if (!IsFinite(halfWidthUnits) || halfWidthUnits <= 0.0)
                {
                    Log($"WARN: TryAppendOffsetRoadEdges invalid halfWidthUnits: {halfWidthUnits}");
                    return false;
                }

                DBObjectCollection left = center.GetOffsetCurves(halfWidthUnits);
                DBObjectCollection right = center.GetOffsetCurves(-halfWidthUnits);

                AppendOffsetCurves(tr, ms, left, layerName);
                AppendOffsetCurves(tr, ms, right, layerName);
                return true;
            }
            catch (Exception ex)
            {
                Log($"WARN: Error in TryAppendOffsetRoadEdges: {ex.Message}");
                return false;
            }
        }

        private static int AppendOffsetCurves(
            Transaction tr, BlockTableRecord ms,
            DBObjectCollection curves, string layerName)
        {
            int count = 0;
            foreach (DBObject obj in curves)
            {
                if (obj is Entity ent)
                {
                    ent.Layer = layerName;
                    ms.AppendEntity(ent);
                    tr.AddNewlyCreatedDBObject(ent, true);
                    count++;
                }
                else
                {
                    obj.Dispose();
                }
            }
            return count;
        }
    }
}
