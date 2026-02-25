using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;
using sisRUA.Core.DTOs;

namespace sisRUA.Engine
{
    /// <summary>
    /// Factory responsible for creating AutoCAD entities with embedded BIM metadata (XData).
    /// Enforces the "BIM Enforcement" requirement of Phase 10.
    /// </summary>
    public static class CadFeatureFactory
    {
        private const string AppName = "sisRUA_BIM";

        /// <summary>
        /// Attaches metadata dictionary as XData to a DBObject.
        /// Ensure Transaction is active.
        /// </summary>
        public static void AttachMetadata(DBObject obj, Dictionary<string, object> metadata, Transaction tr)
        {
            if (obj == null || metadata == null || metadata.Count == 0) return;

            // Ensure Application Name is registered
            RegAppTable rat = (RegAppTable)tr.GetObject(obj.Database.RegAppTableId, OpenMode.ForRead);
            if (!rat.Has(AppName))
            {
                rat.UpgradeOpen();
                var ratRec = new RegAppTableRecord { Name = AppName };
                rat.Add(ratRec);
                tr.AddNewlyCreatedDBObject(ratRec, true);
            }

            // Build XData buffer
            // 1001: AppName
            // 1000: "Key=Value" string pairs (simplest universal storage)
            var rbChain = new ResultBuffer();
            rbChain.Add(new TypedValue((int)DxfCode.ExtendedDataRegAppName, AppName));

            foreach (var kvp in metadata)
            {
                string safeValue = kvp.Value?.ToString() ?? "";
                string entry = $"{kvp.Key}={safeValue}";
                
                // Truncate if too long (DXF 1000 limit is 255 chars, effectively less)
                // Just splitting logic if needed, but for now assuming fits.
                // Or better: Use 1000 for Key, 1000 for Value for structured parsing
                // Strategy: "Key=Value"
                rbChain.Add(new TypedValue((int)DxfCode.ExtendedDataAsciiString, entry));
            }

            obj.UpgradeOpen();
            obj.XData = rbChain;
        }

        public static void AttachMetadata(DBObject obj, Dictionary<string, string> metadata, Transaction tr)
        {
            if (metadata == null) return;
            var objMeta = new Dictionary<string, object>();
            foreach(var kv in metadata) objMeta[kv.Key] = kv.Value;
            AttachMetadata(obj, objMeta, tr);
        }

        public static Polyline CreatePolyline(IEnumerable<SisRuaPoint> points, bool close = false)
        {
            var pline = new Polyline();
            int i = 0;
            foreach (var pt in points)
            {
                // Enforce 2.5D: LightweightPolyline vertices are always 2D (X, Y)
                pline.AddVertexAt(i++, new Point2d(pt.X, pt.Y), 0, 0, 0);
            }
            if (close) pline.Closed = true;
            return pline;
        }

        /// <summary>
        /// Creates a 2.5D Line. While AutoCAD Lines support 3D, we enforce 2.5D 
        /// by ensuring the Z value is consistent (constant elevation) across vertices 
        /// if provided, or flattened to the start point's Z.
        /// </summary>
        public static Line CreateLine(SisRuaPoint start, SisRuaPoint end)
        {
            // 2.5D Enforcement: The line is created at the start point's elevation
            // variance in Z between vertices is disallowed in 2.5D.
            return new Line(new Point3d(start.X, start.Y, start.Z), 
                            new Point3d(end.X, end.Y, start.Z)); 
        }
    }
}
