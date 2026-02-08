using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.Geometry;
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Colors;
using Autodesk.AutoCAD.EditorInput;
using System.IO;

namespace sisRUA.Engine
{
    public class AutoCADDrawingEngine : IDrawingEngine
    {
        public void WriteMessage(string message)
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            if (doc != null)
            {
                doc.Editor.WriteMessage($"\n[sisRUA] {message}");
            }
        }

        public void ClearModelSpace()
        {
            // Implementation left as future exercise or copy from Commands
        }

        public void SaveProject(string projectId, string projectName, string crs, IEnumerable<object> features)
        {
             // implementation delegated to repository usually, but engine can coordinate
             // Unused in current context but required by interface
        }

        public void EnsureLayer(string layerName, short colorIndex)
        {
            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                var lt = (LayerTable)tr.GetObject(db.LayerTableId, OpenMode.ForRead);
                if (!lt.Has(layerName))
                {
                    var ltr = new LayerTableRecord();
                    ltr.Name = layerName;
                    ltr.Color = Color.FromColorIndex(ColorMethod.ByAci, colorIndex);
                    
                    lt.UpgradeOpen();
                    lt.Add(ltr);
                    tr.AddNewlyCreatedDBObject(ltr, true);
                }
            });
        }

        public void InsertBlock(string blockName, SisRuaPoint position, double rotation, double scale, string layerName, Dictionary<string, string> metadata = null)
        {
             SisRuaTransactionalShield.Execute((doc, db, tr) =>
             {
                 var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                 if (!bt.Has(blockName))
                 {
                     WriteMessage($"Bloco '{blockName}' não encontrado.");
                     return;
                 }

                 var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
                 var acadPos = new Point3d(position.X, position.Y, position.Z);
                 
                 using (var bref = new BlockReference(acadPos, bt[blockName]))
                 {
                     bref.Rotation = rotation;
                     bref.ScaleFactors = new Scale3d(scale);
                     bref.Layer = layerName;
                     
                     ms.AppendEntity(bref);
                     tr.AddNewlyCreatedDBObject(bref, true);

                     if (metadata != null && metadata.Count > 0)
                     {
                         CadFeatureFactory.AttachMetadata(bref, metadata, tr);
                     }
                 }
             });
        }
        
        public void DrawPolyline(IEnumerable<SisRuaPoint> points, string layerName, double? constantWidth, double? elevation, string color, Dictionary<string, string> metadata = null)
        {
            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                var pline = new Polyline();
                int i = 0;
                foreach (var pt in points)
                {
                    pline.AddVertexAt(i++, new Point2d(pt.X, pt.Y), 0, 0, 0);
                }

                if (pline.NumberOfVertices < 2)
                {
                    pline.Dispose();
                    return;
                }

                pline.Layer = layerName;
                if (constantWidth.HasValue) pline.ConstantWidth = constantWidth.Value;
                if (elevation.HasValue) pline.Elevation = elevation.Value;
                
                // Color parsing simplified
                if (!string.IsNullOrWhiteSpace(color))
                {
                    // Logic to parse color string... for now simplified
                }

                ms.AppendEntity(pline);
                tr.AddNewlyCreatedDBObject(pline, true);

                if (metadata != null && metadata.Count > 0)
                {
                    CadFeatureFactory.AttachMetadata(pline, metadata, tr);
                }
            });
        }

        public void DrawLine(SisRuaPoint start, SisRuaPoint end, string layerName) 
        {
            var acadStart = new Point3d(start.X, start.Y, start.Z);
            var acadEnd = new Point3d(end.X, end.Y, end.Z);

            SisRuaTransactionalShield.Execute((doc, db, tr) =>
            {
                 var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                 var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
                 
                 var line = new Line(acadStart, acadEnd);
                 line.Layer = layerName;
                 ms.AppendEntity(line);
                 tr.AddNewlyCreatedDBObject(line, true);
            });
        }
    }
}
