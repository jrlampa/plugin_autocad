// Commands/SisRuaBimCommands.cs
// Comando para inspeção de metadados BIM-LITE (XData) em entidades selecionadas.
using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Text;

namespace sisRUA
{
    public partial class SisRuaCommands
    {
        [CommandMethod("SISRUA_VER_BIM")]
        public void VerifyBimMetadata()
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return;
            Editor ed = doc.Editor;
            Database db = doc.Database;

            PromptEntityOptions peo = new PromptEntityOptions("\nSelecione uma entidade para ver dados BIM: ");
            peo.SetRejectMessage("\nSomente entidades gráficas.");
            peo.AddAllowedClass(typeof(Entity), true);
            
            PromptEntityResult per = ed.GetEntity(peo);
            if (per.Status != PromptStatus.OK) return;

            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                Entity ent = (Entity)tr.GetObject(per.ObjectId, OpenMode.ForRead);
                ResultBuffer rb = ent.GetXDataForApplication("sisRUA_BIM");

                if (rb == null)
                {
                    ed.WriteMessage("\n[sisRUA] Nenhuma informação BIM encontrada para o sisRUA nesta entidade.");
                }
                else
                {
                    StringBuilder sb = new StringBuilder();
                    sb.AppendLine("\n── Metadados BIM (sisRUA) ──");
                    
                    TypedValue[] vals = rb.AsArray();
                    // vals[0] é o AppName (1001)
                    // Pares subsequentes (1000)
                    for (int i = 1; i < vals.Length; i += 2)
                    {
                        if (i + 1 < vals.Length)
                        {
                            string key = vals[i].Value?.ToString() ?? "???";
                            string val = vals[i+1].Value?.ToString() ?? "";
                            sb.AppendLine($"{key}: {val}");
                        }
                    }
                    ed.WriteMessage(sb.ToString());
                }
                tr.Commit();
            }
        }
    }
}
