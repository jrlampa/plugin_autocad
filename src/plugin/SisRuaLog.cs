using System;
using System.Diagnostics;
using System.IO;

namespace sisRUA
{
    public static class SisRuaLog
    {
        private static TextWriter _fileLogger;

        public static void SetFileLogger(TextWriter logger)
        {
            _fileLogger = logger;
        }

        public static void Info(string message) => Log("INFO", message);
        public static void Warn(string message) => Log("WARN", message);
        public static void Error(string message) => Log("ERROR", message);
        public static void Debug(string message) => Log("DEBUG", message);

        public static void Log(string level, string message)
        {
            string formatted = $"[{level}] {message}";
            
            // Log to System.Diagnostics.Debug (visible in debug output/tests)
            System.Diagnostics.Debug.WriteLine($"[sisRUA] {formatted}");

            // Log to file if available
            try
            {
                _fileLogger?.WriteLine($"{DateTime.Now:O} {formatted}");
            }
            catch { /* ignore */ }

            // Note: Editor logging must be handled by the caller or via a delegate
            // to avoid AutoCAD dependency here.
            OnMessageLogged?.Invoke(formatted);
        }

        public static event Action<string> OnMessageLogged;
    }
}
