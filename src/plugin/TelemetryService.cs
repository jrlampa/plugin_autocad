using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;

namespace sisRUA
{
    /// <summary>
    /// Lightweight service for silent telemetry and crash reporting.
    /// Sends anonymous error reports to the local Python backend.
    /// </summary>
    public static class TelemetryService
    {
        private static readonly HttpClient _client = new HttpClient { Timeout = TimeSpan.FromSeconds(5) };
        private const string TelemetryEndpoint = "http://localhost:8000/audit/telemetry";

        public static async Task ReportError(string component, Exception ex, string context = null)
        {
            try
            {
                var payload = new
                {
                    timestamp = DateTime.UtcNow.ToString("o"),
                    level = "ERROR",
                    component = component,
                    message = ex.Message,
                    stack_trace = ex.StackTrace,
                    context = context,
                    os = Environment.OSVersion.ToString(),
                    version = "1.0.0"
                };

                var json = JsonSerializer.Serialize(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                // Silent fire-and-forget
                await _client.PostAsync(TelemetryEndpoint, content).ConfigureAwait(false);
            }
            catch
            {
                // Never crash the plugin due to telemetry failure
            }
        }

        public static void ReportErrorSync(string component, Exception ex, string context = null)
        {
            Task.Run(() => ReportError(component, ex, context));
        }
    }
}
