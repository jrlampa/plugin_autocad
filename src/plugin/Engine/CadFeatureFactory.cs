using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.Geometry;

namespace sisRUA.Engine
{
    public static class CadFeatureFactory
    {
        public const string RegAppName = "SISRUA";

        /// <summary>
        /// Registers the SISRUA application name in the RegAppTable if not present.
        /// Must be called within a transaction.
        /// </summary>
        public static void EnsureRegApp(Transaction tr, Database db)
        {
            var rat = (RegAppTable)tr.GetObject(db.RegAppTableId, OpenMode.ForRead);
            if (!rat.Has(RegAppName))
            {
                rat.UpgradeOpen();
                var rar = new RegAppTableRecord { Name = RegAppName };
                rat.Add(rar);
                tr.AddNewlyCreatedDBObject(rar, true);
            }
        }

        /// <summary>
        /// Attaches functionality/semantic data to an entity via XData.
        /// Format:
        /// 1001: SISRUA
        /// 1000: key1=value1
        /// 1000: key2=value2
        /// ...
        /// </summary>
        public static void AttachMetadata(Entity entity, Dictionary<string, string> metadata, Transaction tr)
        {
            if (metadata == null || metadata.Count == 0) return;

            EnsureRegApp(tr, entity.Database);

            var rb = new ResultBuffer();
            rb.Add(new TypedValue((int)DxfCode.ExtendedDataRegAppName, RegAppName));

            foreach (var kvp in metadata)
            {
                // XData string limit is 255 chars.
                string entry = $"{kvp.Key}={kvp.Value}";
                if (entry.Length > 255) entry = entry.Substring(0, 255);
                
                rb.Add(new TypedValue((int)DxfCode.ExtendedDataAsciiString, entry));
            }

            entity.XData = rb;
        }

        public static Polyline CreatePolyline(IEnumerable<Point2d> points, string layer, Dictionary<string, string> metadata, double width = 0, double elevation = 0)
        {
            var pline = new Polyline();
            int i = 0;
            foreach (var pt in points)
            {
                pline.AddVertexAt(i++, pt, 0, 0, 0);
            }

            pline.Layer = layer;
            if (width > 0) pline.ConstantWidth = width;
            if (elevation != 0) pline.Elevation = elevation;

            // Metadata is attached later when added to DB/Trans, 
            // OR we can attach it assuming the caller handles the Transaction/RegApp check.
            // Ideally, caller calls AttachMetadata after adding to DB, or we can't attach XData easily without DB context for RegApp check?
            // Actually, we can attach XData to a non-database-resident object, BUT we can't ensure RegApp exists without DB.
            // So we will assume the caller uses a wrapper that calls EnsureRegApp or does it manually.
            // However, to make this "Factory" useful, it should return the object, and metadata attachment might happen inside the existing TransactionalShield.
            
            return pline;
        }
        
        // Since we need a Transaction to EnsureRegApp, let's keep AttachMetadata separate 
        // or require passing Trasaction to the create methods if we want to do it all at once.
        // For simplicity in refactoring, we'll expose AttachMetadata and let the Engine call it.
    }
}
