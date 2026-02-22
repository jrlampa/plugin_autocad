// Commands/SisRuaCommandDtos.cs
// DTOs privados usados pelos comandos sisRUA para serialização/deserialização HTTP.
// Separados de SisRuaCommands.cs para manter cada arquivo abaixo de 500 linhas (SoC).
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace sisRUA
{
    public partial class SisRuaCommands
    {
        private sealed class PrepareOsmRequest
        {
            [JsonPropertyName("latitude")]
            public double Latitude { get; set; }

            [JsonPropertyName("longitude")]
            public double Longitude { get; set; }

            [JsonPropertyName("radius")]
            public double Radius { get; set; }
        }

        private sealed class PrepareGeoJsonRequest
        {
            [JsonPropertyName("geojson")]
            public string GeoJson { get; set; }
        }

        private sealed class PrepareResponse
        {
            [JsonPropertyName("crs_out")]
            public string CrsOut { get; set; }

            [JsonPropertyName("features")]
            public List<Core.DTOs.CadFeatureDto> Features { get; set; }
        }

        private sealed class PrepareJobRequest
        {
            [JsonPropertyName("kind")]
            public string Kind { get; set; }

            [JsonPropertyName("latitude")]
            public double? Latitude { get; set; }

            [JsonPropertyName("longitude")]
            public double? Longitude { get; set; }

            [JsonPropertyName("radius")]
            public double? Radius { get; set; }

            [JsonPropertyName("geojson")]
            public string GeoJson { get; set; }
        }

        private sealed class JobStatusResponse
        {
            [JsonPropertyName("job_id")]
            public string JobId { get; set; }

            [JsonPropertyName("kind")]
            public string Kind { get; set; }

            [JsonPropertyName("status")]
            public string Status { get; set; }

            [JsonPropertyName("progress")]
            public double Progress { get; set; }

            [JsonPropertyName("message")]
            public string Message { get; set; }

            [JsonPropertyName("result")]
            public JsonElement Result { get; set; }

            [JsonPropertyName("error")]
            public string Error { get; set; }
        }

        private sealed class SyncToCloudResponse
        {
            [JsonPropertyName("status")]
            public string Status { get; set; }

            [JsonPropertyName("synced_features")]
            public int SyncedFeatures { get; set; }

            [JsonPropertyName("cloud_node")]
            public string CloudNode { get; set; }

            [JsonPropertyName("timestamp")]
            public double Timestamp { get; set; }
        }
    }
}
