using System;
using System.IO;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace sisRUA
{
    internal static class SisRuaSettings
    {
        private sealed class SettingsModel
        {
            [JsonPropertyName("meters_to_units")]
            public double? MetersToUnits { get; set; }

            // Aviso de privacidade (LGPD) aceito pelo usuário ao abrir o plugin pela primeira vez.
            [JsonPropertyName("privacy_notice_accepted")]
            public bool? PrivacyNoticeAccepted { get; set; }

            [JsonPropertyName("privacy_notice_accepted_at_utc")]
            public string PrivacyNoticeAcceptedAtUtc { get; set; }
        }

        private static string GetSettingsPath()
        {
            string baseDir = null;
            try { baseDir = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData); } catch { /* ignore */ }
            if (string.IsNullOrWhiteSpace(baseDir)) return null;
            return Path.Combine(baseDir, "sisRUA", "settings.json");
        }

        private static SettingsModel ReadModelOrNew()
        {
            try
            {
                string path = GetSettingsPath();
                if (string.IsNullOrWhiteSpace(path) || !File.Exists(path))
                {
                    return new SettingsModel();
                }

                string text = File.ReadAllText(path);
                var model = JsonSerializer.Deserialize<SettingsModel>(text, new JsonSerializerOptions { PropertyNameCaseInsensitive = true });
                return model ?? new SettingsModel();
            }
            catch
            {
                return new SettingsModel();
            }
        }

        private static bool TryWriteModel(SettingsModel model)
        {
            try
            {
                string path = GetSettingsPath();
                if (string.IsNullOrWhiteSpace(path)) return false;

                Directory.CreateDirectory(Path.GetDirectoryName(path));
                string text = JsonSerializer.Serialize(model ?? new SettingsModel(), new JsonSerializerOptions { WriteIndented = true });
                File.WriteAllText(path, text);
                return true;
            }
            catch
            {
                return false;
            }
        }

        public static string TryGetSettingsPathForDisplay()
        {
            return GetSettingsPath();
        }

        public static double? TryReadMetersToUnits()
        {
            try
            {
                var model = ReadModelOrNew();
                if (model?.MetersToUnits == null) return null;
                double v = model.MetersToUnits.Value;
                if (double.IsNaN(v) || double.IsInfinity(v) || v <= 0.0) return null;
                return v;
            }
            catch
            {
                return null;
            }
        }

        public static bool TryWriteMetersToUnits(double metersToUnits)
        {
            try
            {
                if (double.IsNaN(metersToUnits) || double.IsInfinity(metersToUnits) || metersToUnits <= 0.0)
                {
                    return false;
                }

                var model = ReadModelOrNew();
                model.MetersToUnits = metersToUnits;
                return TryWriteModel(model);
            }
            catch
            {
                return false;
            }
        }

        public static bool IsPrivacyNoticeAccepted()
        {
            try
            {
                var model = ReadModelOrNew();
                return model?.PrivacyNoticeAccepted == true;
            }
            catch
            {
                return false;
            }
        }

        public static bool TryMarkPrivacyNoticeAccepted()
        {
            try
            {
                var model = ReadModelOrNew();
                model.PrivacyNoticeAccepted = true;
                model.PrivacyNoticeAcceptedAtUtc = DateTime.UtcNow.ToString("O");
                return TryWriteModel(model);
            }
            catch
            {
                return false;
            }
        }
    }
}

