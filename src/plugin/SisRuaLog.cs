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

        private static readonly System.Text.RegularExpressions.Regex _emailRegex = new System.Text.RegularExpressions.Regex(@"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}");
        private static readonly System.Text.RegularExpressions.Regex _userPathRegex = new System.Text.RegularExpressions.Regex(@"(?<=Users[\\/])[^\\/]+");

        public static void Log(string level, string message)
        {
            string sanitizedMessage = SanitizeMessage(message);
            string formatted = $"[{level}] {sanitizedMessage}";
            
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
