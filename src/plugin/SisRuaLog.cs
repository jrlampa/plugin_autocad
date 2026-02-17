using System;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;

namespace sisRUA
{
    public static class SisRuaLog
    {
        private static TextWriter _fileLogger;
        private static readonly object _debugLogLock = new object();
        private static readonly string DebugLogPath = GetDebugLogPath();

        private static string GetDebugLogPath()
        {
            try
            {
                string asmDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly()?.Location);
                if (!string.IsNullOrEmpty(asmDir))
                    return Path.Combine(asmDir, "debug.log");
            }
            catch { }
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "sisRUA", "debug.log");
        }

        // #region agent log
        /// <summary>Appends one NDJSON line for debug session analysis (next to DLL or LocalAppData\sisRUA).</summary>
        public static void WriteDebugLine(string location, string message, object data, string hypothesisId, string runId = "run1")
        {
            string dataJson = "null";
            try { dataJson = data != null ? JsonSerializer.Serialize(data) : "null"; } catch { dataJson = "{}"; }
            long ts = DateTimeOffset.UtcNow.ToUnixTimeMilliseconds();
            string line = "{\"id\":\"log_" + ts + "\",\"timestamp\":" + ts + ",\"location\":\"" + Escape(location) + "\",\"message\":\"" + Escape(message) + "\",\"data\":" + dataJson + ",\"runId\":\"" + Escape(runId) + "\",\"hypothesisId\":\"" + Escape(hypothesisId) + "\"}" + Environment.NewLine;
            lock (_debugLogLock)
            {
                try { WriteToPath(DebugLogPath, line); } catch { }
            }
        }
        private static void WriteToPath(string path, string line)
        {
            string dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
            File.AppendAllText(path, line);
        }
        private static string Escape(string s) { return string.IsNullOrEmpty(s) ? "" : s.Replace("\\", "\\\\").Replace("\"", "\\\"").Replace("\r", "").Replace("\n", "\\n"); }
        // #endregion

        public static void SetFileLogger(TextWriter logger)
        {
            _fileLogger = logger;
        }

        public static void Info(string message) => Log("INFO", message);
        public static void Warn(string message) => Log("WARN", message);
        public static void Error(string message) => Log("ERROR", message);
        public static void Debug(string message) => Log("DEBUG", message);

        private static readonly System.Text.RegularExpressions.Regex _emailRegex = new System.Text.RegularExpressions.Regex(@"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}");
        private static readonly System.Text.RegularExpressions.Regex _userPathRegex = new System.Text.RegularExpressions.Regex(@"(?<=Users[\\/])[^\\/]+");

        public static void Log(string level, string message)
        {
            try
            {
                string sanitizedMessage = SanitizeMessage(message);
                string timestamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss.fff");
                string formatted = $"[{timestamp}] [{level}] {sanitizedMessage}";
                
                // Console / Debug output
                System.Diagnostics.Debug.WriteLine($"[sisRUA] {formatted}");

                // File Rotation & Implementation
                string logDir = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "sisRUA", "logs");
                if (!Directory.Exists(logDir)) Directory.CreateDirectory(logDir);

                string logPath = Path.Combine(logDir, "sisrua_plugin.log");
                
                // Simple Rotation: If > 10MB, rotate
                if (File.Exists(logPath) && new FileInfo(logPath).Length > 10 * 1024 * 1024)
                {
                    // #region agent log
                    SisRuaLog.WriteDebugLine("SisRuaLog.cs:Log", "logRotation", new { logPath }, "H4", "run1");
                    // #endregion
                    string oldLog = Path.Combine(logDir, $"sisrua_plugin_{DateTime.Now:yyyyMMdd_HHmmss}.log");
                    File.Move(logPath, oldLog);
                    
                    // Cleanup: Keep only last 7 files
                    var oldFiles = Directory.GetFiles(logDir, "sisrua_plugin_*.log")
                        .OrderByDescending(f => f)
                        .Skip(7);
                    foreach (var f in oldFiles) File.Delete(f);
                }

                File.AppendAllText(logPath, formatted + Environment.NewLine);

                OnMessageLogged?.Invoke(formatted);
            }
            catch { /* Fail-safe for mission-critical AutoCAD environment */ }
        }

        private static string SanitizeMessage(string input)
        {
            if (string.IsNullOrEmpty(input)) return input;
            
            // 1. Mask User Paths (Windows)
            // C:\Users\Jonatas Lampa\AppData -> C:\Users\***\AppData
            try
            {
                input = _userPathRegex.Replace(input, "***");
            }
            catch {}

            // 2. Mask Emails
            try
            {
                // Simple masking, keeps domain somewhat visible or just partial
                // ensuring PII removal is priority
                input = _emailRegex.Replace(input, "***@***.***");
            }
            catch {}

            return input;
        }

        public static event Action<string> OnMessageLogged;
    }
}
