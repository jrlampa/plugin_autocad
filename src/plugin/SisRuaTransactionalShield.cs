using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.DatabaseServices;
using System;
using System.Diagnostics;

namespace sisRUA
{
    /// <summary>
    /// Fornece um wrapper seguro para operações no AutoCAD, garantindo o Lock do documento,
    /// o início de uma transação e (opcionalmente) verificando o georeferenciamento.
    /// </summary>
    public static class SisRuaTransactionalShield
    {
        /// <summary>
        /// Executa uma ação dentro de um contexto seguro (Locked + Transaction).
        /// </summary>
        public static void Execute(Action<Document, Database, Transaction> action)
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null)
            {
                SisRuaLog.Warn("TransactionalShield: Tentativa de execução sem documento ativo.");
                return;
            }

            Database db = doc.Database;
            using (doc.LockDocument())
            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                try
                {
                    // Garantia de Georeferenciamento (Logs se ausente, mas não bloqueia por enquanto para não quebrar fluxos legados)
                    CheckGeoreference(db);

                    action(doc, db, tr);
                    tr.Commit();
                }
                catch (Exception ex)
                {
                    SisRuaLog.Error($"TransactionalShield: Falha na execução: {ex.Message}\n{ex.StackTrace}");
                    tr.Abort();
                    throw; // Repropaga para o chamador tratar (ex: UI mostrar erro)
                }
            }
        }

        /// <summary>
        /// Executa uma função que retorna um valor dentro de um contexto seguro.
        /// </summary>
        public static T Execute<T>(Func<Document, Database, Transaction, T> func)
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return default;

            Database db = doc.Database;
            using (doc.LockDocument())
            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                try
                {
                    CheckGeoreference(db);

                    T result = func(doc, db, tr);
                    tr.Commit();
                    return result;
                }
                catch (Exception ex)
                {
                    SisRuaLog.Error($"TransactionalShield: Falha na execução (com retorno): {ex.Message}");
                    tr.Abort();
                    throw;
                }
            }
        }

        /// <summary>
        /// Executa uma tarefa assíncrona dentro de um contexto seguro.
        /// Útil quando o fluxo envolve IO antes ou durante a transação (embora IO dentro de transação deva ser evitado).
        /// </summary>
        public static async Task ExecuteAsync(Func<Document, Database, Transaction, Task> action)
        {
            Document doc = Application.DocumentManager.MdiActiveDocument;
            if (doc == null) return;

            Database db = doc.Database;
            using (doc.LockDocument())
            using (Transaction tr = db.TransactionManager.StartTransaction())
            {
                try
                {
                    CheckGeoreference(db);
                    await action(doc, db, tr);
                    tr.Commit();
                }
                catch (Exception ex)
                {
                    SisRuaLog.Error($"TransactionalShield: Falha na execução assíncrona: {ex.Message}");
                    tr.Abort();
                    throw;
                }
            }
        }

        private static void CheckGeoreference(Database db)
        {
            if (db.GeoLocationDataId == ObjectId.Null)
            {
                SisRuaLog.Warn("TransactionalShield: O desenho atual NÃO possui dados de Georeferenciamento (GEOLOCALIZACAO).");
                // Futuro: Impedir modificações GIS se ausente?
            }
        }
    }
}
