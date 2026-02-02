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
        }

        public void EnsureLayer(string layerName, short colorIndex)
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return;
            var db = doc.Database;

            using (var tr = db.TransactionManager.StartTransaction())
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
                tr.Commit();
            }
        }

        public void InsertBlock(string blockName, Point3d position, double rotation, double scale, string layerName)
        {
             // Logic moved from SisRuaCommands.InsertBlock
             // Validation: We need the logic to load blocks from files too.
             // For now, assume SisRuaCommands.InsertBlock is public or moved here.
             
             // Simplification for the example:
             var doc = Application.DocumentManager.MdiActiveDocument;
             if (doc == null) return;
             var db = doc.Database;
             
             using (var tr = db.TransactionManager.StartTransaction())
             {
                 var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                 var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);

                 // ... Implementation of block insertion ...
                 // This is complex to move entirely in one go without breaking.
                 // We will create a shim first.
                 
                 // Reuse logic via reflection or simple re-implementation?
                 // Re-implementation is safer for decoupling.
             }
        }
        
        public void DrawLine(Point3d start, Point3d end, string layerName) 
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return;
            var db = doc.Database;
            using (var tr = db.TransactionManager.StartTransaction())
            {
                 var bt = (BlockTable)tr.GetObject(db.BlockTableId, OpenMode.ForRead);
                 var ms = (BlockTableRecord)tr.GetObject(bt[BlockTableRecord.ModelSpace], OpenMode.ForWrite);
                 
                 var line = new Line(start, end);
                 line.Layer = layerName;
                 ms.AppendEntity(line);
                 tr.AddNewlyCreatedDBObject(line, true);
                 tr.Commit();
            }
        }
    }
}
