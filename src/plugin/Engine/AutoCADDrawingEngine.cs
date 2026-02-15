using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Geometry;
using sisRUA.Core.DTOs;

namespace sisRUA.Engine
{
    public class AutoCADDrawingEngine : IDrawingEngine
    {
        private static readonly Dictionary<string, (string layer, short? aci)> _layerStyles = new Dictionary<string, (string, short?)>(StringComparer.OrdinalIgnoreCase)
        {
            ["motorway"] = ("SISRUA_OSM_MOTORWAY", 1),
            ["trunk"] = ("SISRUA_OSM_TRUNK", 2),
            ["primary"] = ("SISRUA_OSM_PRIMARY", 3),
            ["secondary"] = ("SISRUA_OSM_SECONDARY", 4),
            ["tertiary"] = ("SISRUA_OSM_TERTIARY", 5),
            ["residential"] = ("SISRUA_OSM_RESIDENTIAL", 7),
            ["service"] = ("SISRUA_OSM_SERVICE", 8),
            ["unclassified"] = ("SISRUA_OSM_UNCLASSIFIED", 9),
            ["living_street"] = ("SISRUA_OSM_LIVING", 30),
            ["footway"] = ("SISRUA_OSM_PEDESTRIAN", 140),
            ["path"] = ("SISRUA_OSM_PATH", 141),
            ["cycleway"] = ("SISRUA_OSM_CYCLE", 150),
        };

        public void WriteMessage(string message)
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            doc?.Editor.WriteMessage($"\n[sisRUA] {message}");
        }

        public double GetScaleFactor()
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return 1.0;
            return GetMetersToDrawingUnitsScale(doc.Database);
        }

        public async Task DrawFeaturesAsync(IEnumerable<CadFeatureDto> features, string crsOut, IProcessingProgress progress)
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return;
            var db = doc.Database;
            
            double metersToUnits = GetMetersToDrawingUnitsScale(db);
            var featureList = features.ToList();
            
            int createdPolylines = 0;
            int createdBlocks = 0;

            for (int i = 0; i < featureList.Count; i++)
            {
                var f = featureList[i];
                if (f == null) continue;

                var (layerName, aci) = GetLayerStyle(f);

                using (doc.LockDocument())
                {
                    SisRuaTransactionalShield.Execute((d, database, tr) =>
                    {
                        var lt = (LayerTable)tr.GetObject(database.LayerTableId, OpenMode.ForRead);
                        EnsureLayerInternal(tr, database, lt, layerName, aci);
                        
                        var ms = (BlockTableRecord)tr.GetObject(SymbolUtilityServices.GetBlockModelSpaceId(database), OpenMode.ForWrite);

                        switch (f.FeatureType)
                        {
                            case CadFeatureDtoType.Polyline:
                                if (f.CoordsXy == null || f.CoordsXy.Count < 2) break;
                                
                                var points = f.CoordsXy.Select(pt => new Point3d(pt[0] * metersToUnits, pt[1] * metersToUnits, f.Elevation ?? 0)).ToList();
                                var pline = new Polyline(points.Count);
                                for (int j = 0; j < points.Count; j++)
                                {
                                    pline.AddVertexAt(j, new Point2d(points[j].X, points[j].Y), 0, 0, 0);
                                }
                                
                                pline.Layer = layerName;
                                if (f.WidthMeters.HasValue) pline.ConstantWidth = f.WidthMeters.Value * metersToUnits;
                                
                                ms.AppendEntity(pline);
                                tr.AddNewlyCreatedDBObject(pline, true);
                                createdPolylines++;

                                if (f.WidthMeters.HasValue && f.WidthMeters.Value > 2.0)
                                {
                                    TryAppendOffsetEdges(tr, ms, pline, (f.WidthMeters.Value * metersToUnits) / 2.0, layerName);
                                }
                                break;

                            case CadFeatureDtoType.Point:
                                if (f.InsertionPointXy == null || f.InsertionPointXy.Count < 2) break;
                                
                                var insPt = new Point3d(f.InsertionPointXy[0] * metersToUnits, f.InsertionPointXy[1] * metersToUnits, f.Elevation ?? 0);
                                var blockDefId = EnsureBlockLoaded(tr, database, f.BlockName, f.BlockFilePath);
                                
                                var bref = new BlockReference(insPt, blockDefId);
                                bref.Layer = layerName;
                                bref.ScaleFactors = new Scale3d(f.Scale ?? 1.0);
                                bref.Rotation = f.Rotation ?? 0.0;
                                
                                ms.AppendEntity(bref);
                                tr.AddNewlyCreatedDBObject(bref, true);
                                createdBlocks++;
                                break;
                        }
                    });
                }

                if (i % 10 == 0)
                {
                    progress?.SetProgress(75 + (int)(25.0 * i / featureList.Count));
                    progress?.UpdateScreen();
                    await Task.Delay(5);
                }

                if (progress != null && progress.WasCancelled) break;
            }

            WriteMessage($"Sucesso! {createdPolylines} polylines e {createdBlocks} blocos criados.");
        }

        public void EnsureLayer(string layerName, short colorIndex)
        {
            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                var lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
                EnsureLayerInternal(tr, db, lt, layerName, colorIndex);
            });
        }

        public void InjectAuditMetadata(string projectId)
        {
            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                var nod = (DBDictionary)tr.GetObject(db.NamedObjectsDictionaryId, OpenMode.ForWrite);
                if (!nod.Contains("SISRUA_METADATA"))
                {
                    var dict = new DBDictionary();
                    nod.SetAt("SISRUA_METADATA", dict);
                    tr.AddNewlyCreatedDBObject(dict, true);

                    var xrec = new Xrecord();
                    xrec.Data = new ResultBuffer(
                        new TypedValue((int)DxfCode.Text, projectId),
                        new TypedValue((int)DxfCode.Text, DateTime.UtcNow.ToString("O")),
                        new TypedValue((int)DxfCode.Text, "Padrão sisRUA v1.1.0")
                    );
                    dict.SetAt("Audit_ID", xrec);
                    tr.AddNewlyCreatedDBObject(xrec, true);
                }
            });
        }

        public void ClearModelSpace() { /* Placeholder */ }
        public void SaveProject(string projectId, string projectName, string crs, IEnumerable<CadFeatureDto> features) { /* Placeholder */ }
        public void InsertBlock(string blockName, SisRuaPoint position, double rotation, double scale, string layerName, Dictionary<string, string> metadata = null) { /* Placeholder */ }
        public void DrawLine(SisRuaPoint start, SisRuaPoint end, string layerName, Dictionary<string, string> metadata = null) { /* Placeholder */ }
        public void DrawPolyline(IEnumerable<SisRuaPoint> points, string layerName, double? constantWidth, double? elevation, string color, Dictionary<string, string> metadata = null) { /* Placeholder */ }

        private void EnsureLayerInternal(Transaction tr, Database db, LayerTable lt, string layerName, short? aci)
        {
            if (lt.Has(layerName)) return;
            lt.UpgradeOpen();
            var ltr = new LayerTableRecord { Name = layerName };
            if (aci.HasValue) ltr.Color = Color.FromColorIndex(ColorMethod.ByAci, aci.Value);
            lt.Add(ltr);
            tr.AddNewlyCreatedDBObject(ltr, true);
        }

        private ObjectId EnsureBlockLoaded(Transaction tr, Database db, string name, string path)
        {
            var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
            if (bt.Has(name)) return bt[name];
            if (string.IsNullOrEmpty(path) || !File.Exists(path)) return ObjectId.Null;

            using (var blockDb = new Database(false, true))
            {
                blockDb.ReadDwgFile(path, FileShare.Read, true, "");
                return db.Insert(name, blockDb, true);
            }
        }

        private (string layer, short? aci) GetLayerStyle(CadFeatureDto f)
        {
            if (!string.IsNullOrEmpty(f.Highway) && _layerStyles.TryGetValue(f.Highway, out var style)) return style;
            return (f.Layer ?? "SISRUA_VIAS", null);
        }

        private void TryAppendOffsetEdges(Transaction tr, BlockTableRecord ms, Polyline center, double halfWidth, string layer)
        {
            try
            {
                var left = center.GetOffsetCurves(halfWidth);
                var right = center.GetOffsetCurves(-halfWidth);
                foreach (Entity ent in left.Cast<Entity>().Concat(right.Cast<Entity>()))
                {
                    ent.Layer = layer;
                    ms.AppendEntity(ent);
                    tr.AddNewlyCreatedDBObject(ent, true);
                }
            }
            catch { }
        }

        private double GetMetersToDrawingUnitsScale(Database db)
        {
            short insunits = (short)Application.GetSystemVariable("INSUNITS");
            switch (insunits)
            {
                case 1: return 39.3701; // Inches
                case 4: return 1000.0; // mm
                case 5: return 100.0;  // cm
                case 6: return 1.0;    // Meters
                default: return 1.0;
            }
        }
    }
}
