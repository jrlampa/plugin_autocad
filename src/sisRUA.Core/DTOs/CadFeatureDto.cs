using System;
using System.Collections.Generic;
using System.Text.Json.Serialization;

namespace sisRUA.Core.DTOs
{
    public enum CadFeatureDtoType
    {
        Polyline,
        Point,
        Text
    }

    public sealed class CadFeatureDto
    {
        [JsonPropertyName("feature_type")]
        public CadFeatureDtoType FeatureType { get; set; } = CadFeatureDtoType.Polyline;

        [JsonPropertyName("layer")]
        public string Layer { get; set; }

        [JsonPropertyName("name")]
        public string Name { get; set; }

        [JsonPropertyName("highway")]
        public string Highway { get; set; }

        [JsonPropertyName("width_m")]
        public double? WidthMeters { get; set; }

        [JsonPropertyName("coords_xy")]
        public List<List<double>> CoordsXy { get; set; }

        [JsonPropertyName("insertion_point_xy")]
        public List<double> InsertionPointXy { get; set; }

        [JsonPropertyName("block_name")]
        public string BlockName { get; set; }

        [JsonPropertyName("block_filepath")]
        public string BlockFilePath { get; set; }

        [JsonPropertyName("rotation")]
        public double? Rotation { get; set; }

        [JsonPropertyName("scale")]
        public double? Scale { get; set; }
        [JsonPropertyName("elevation")]
        public double? Elevation { get; set; }

        [JsonPropertyName("color")]
        public string Color { get; set; }

        [JsonPropertyName("slope")]
        public double? Slope { get; set; }

        [JsonPropertyName("original_geojson_properties")]
        public Dictionary<string, object> OriginalGeoJsonProperties { get; set; }

        [JsonPropertyName("text_content")]
        public string TextContent { get; set; }
    }
}
