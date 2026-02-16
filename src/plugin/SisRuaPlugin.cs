using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.ApplicationServices.Core;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using sisRUA.Core;
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;

[assembly: ExtensionApplication(typeof(sisRUA.SisRuaPlugin))]
[assembly: CommandClass(typeof(sisRUA.SisRuaPalette))]
[assembly: CommandClass(typeof(sisRUA.SisRuaCommands))]

namespace sisRUA
{
    using Exception = System.Exception;

    /// <summary>
    /// Gerencia o ciclo de vida do plugin e delega o controle do processo backend para o BackendManager.
    /// </summary>
    public class SisRuaPlugin : IExtensionApplication
    {
        public static SisRuaPlugin Instance { get; private set; }
        public BackendManager BackendManager { get; private set; }

        // --- Propriedades Estáticas para Compatibilidade ---
        public static int BackendPort => Instance?.BackendManager?.Port ?? 0;
        public static string BackendBaseUrl => Instance?.BackendManager?.BaseUrl;
        public static string BackendAuthToken => Instance?.BackendManager?.AuthToken;
        public const string BackendAuthHeaderName = BackendManager.AuthHeaderName;

        public static bool EnsureBackendHealthy(TimeSpan timeout)
        {
            return Instance?.BackendManager?.EnsureHealthy(timeout) ?? false;
        }

        public static string GetLocalSisRuaDir()
        {
             string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
             return Path.Combine(localAppData, "sisRUA");
        }

        private static TextWriter _logger;

        /// <summary>
        /// Chamado quando o AutoCAD carrega a extensão.
        /// </summary>
        public void Initialize()
        {
            Instance = this;
            SetupLogger();
            SisRuaLog.OnMessageLogged += (msg) => LogToEditor(msg);
            
            LogToEditor("\n>>> sisRUA Plugin: Initialize() called.");

            AppDomain.CurrentDomain.AssemblyResolve += CurrentDomain_AssemblyResolve;

            try
            {
                BackendManager = new BackendManager();
                BackendManager.OnLog = (msg) => LogToEditor(msg);
                BackendManager.OnAlert = (msg) => LogAndAlert(msg);
                
                // Inicia o backend (gerenciamento de processo interno)
                BackendManager.Start();
            }
            catch (Exception ex)
            {
                LogAndAlert("Erro durante Initialize(): " + ex.Message);
            }
        }

        public void Terminate()
        {
            LogToEditor("\n>>> sisRUA Plugin: Terminate() called.");
            try
            {
                // Garante que o processo morre IMEDIATAMENTE ao fechar o AutoCAD
                BackendManager?.Stop();
                BackendManager = null;
            }
            catch (Exception ex)
            {
                LogToEditor($"\n[ERROR] Exceção ao finalizar: {ex.Message}");
            }
            finally
            {
                _logger?.Close();
                _logger = null;
            }
        }

        private void LogToEditor(string message)
        {
            var doc = Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument;
            if (doc != null)
            {
                doc.Editor.WriteMessage($"\n[sisRUA] {message.Trim()}");
            }
            Debug.WriteLine($"[sisRUA] {message.Trim()}");
            _logger?.WriteLine($"[INFO] {message.Trim()}");
        }

        private void LogAndAlert(string message)
        {
            LogToEditor(message);
            Autodesk.AutoCAD.ApplicationServices.Application.ShowAlertDialog(message);
            _logger?.WriteLine($"[ALERT] {message.Trim()}");
        }

        private void SetupLogger()
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return;

                string logDir = Path.Combine(localSisRuaDir, "logs");
                Directory.CreateDirectory(logDir);

                string logFileName = $"sisRUA_plugin_{DateTime.Now:yyyyMMdd_HHmmss}.log";
                string logFilePath = Path.Combine(logDir, logFileName);

                _logger = TextWriter.Synchronized(new StreamWriter(logFilePath, append: true, Encoding.UTF8) { AutoFlush = true });
                SisRuaLog.SetFileLogger(_logger);
                _logger.WriteLine($"--- sisRUA Plugin Log Started: {DateTime.Now} ---");
            }
            catch (Exception ex)
            {
                Debug.WriteLine($"[sisRUA] ERROR: Failed to setup logger: {ex.Message}");
            }
        }

        private Assembly CurrentDomain_AssemblyResolve(object sender, ResolveEventArgs args)
        {
            string assemblyName = new AssemblyName(args.Name).Name + ".dll";
            string assemblyPath = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string fullPath = Path.Combine(assemblyPath, assemblyName);

            if (File.Exists(fullPath))
            {
                return Assembly.LoadFrom(fullPath);
            }
            return null;
        }
    }
}