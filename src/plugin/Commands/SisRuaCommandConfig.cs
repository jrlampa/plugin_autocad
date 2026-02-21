// Commands/SisRuaCommandConfig.cs
// Configuração de camadas e blocos: tipos de via → layers CAD, tipos de ponto → blocos DWG.
// Suporta override por arquivo JSON em Resources/ para customização sem recompilação.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace sisRUA
{
    public partial class SisRuaCommands
    {
        // ──────────────────────────────────────────────────────────────────────────
        // Tipos de configuração
        // ──────────────────────────────────────────────────────────────────────────

        private sealed class LayerStyle
        {
            [JsonPropertyName("layer")]
            public string Layer { get; set; }

            [JsonPropertyName("aci")]
            public short? Aci { get; set; }
        }

        private sealed class LayersConfig
        {
            [JsonPropertyName("highway")]
            public Dictionary<string, LayerStyle> Highway { get; set; }
        }

        private sealed class BlockMapEntry
        {
            [JsonPropertyName("block_name")]
            public string BlockName { get; set; }

            [JsonPropertyName("block_filepath")]
            public string BlockFilePath { get; set; }

            [JsonPropertyName("layer")]
            public string Layer { get; set; }

            [JsonPropertyName("scale")]
            public double? Scale { get; set; }

            [JsonPropertyName("rotation")]
            public double? Rotation { get; set; }
        }

        private sealed class BlockMapConfig
        {
            [JsonPropertyName("default_block_path")]
            public string DefaultBlockPath { get; set; }

            [JsonPropertyName("mappings")]
            public Dictionary<string, BlockMapEntry> Mappings { get; set; }
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Instâncias lazy (thread-safe, carregadas na primeira utilização)
        // ──────────────────────────────────────────────────────────────────────────

        private static readonly Lazy<Dictionary<string, LayerStyle>> _highwayLayerMap =
            new Lazy<Dictionary<string, LayerStyle>>(LoadHighwayLayerMap, isThreadSafe: true);

        private static readonly Lazy<Dictionary<string, BlockMapEntry>> _blockMapping =
            new Lazy<Dictionary<string, BlockMapEntry>>(LoadBlockMapping, isThreadSafe: true);

        // ──────────────────────────────────────────────────────────────────────────
        // Carregamento de mapeamento de blocos
        // ──────────────────────────────────────────────────────────────────────────

        private static Dictionary<string, BlockMapEntry> LoadBlockMapping()
        {
            var map = new Dictionary<string, BlockMapEntry>(StringComparer.OrdinalIgnoreCase);

            try
            {
                string asmDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                if (!string.IsNullOrWhiteSpace(asmDir))
                {
                    string cfgPath = Path.Combine(asmDir, "Resources", "blocks_mapping.json");

                    if (!File.Exists(cfgPath))
                    {
                        string bundleResources = Path.Combine(
                            Directory.GetParent(asmDir).FullName, "Resources", "blocks_mapping.json");
                        if (File.Exists(bundleResources))
                            cfgPath = bundleResources;
                    }

                    if (File.Exists(cfgPath))
                    {
                        string text = File.ReadAllText(cfgPath);
                        var cfg = JsonSerializer.Deserialize<BlockMapConfig>(text, _jsonOptions);
                        if (cfg?.Mappings != null)
                        {
                            foreach (var kv in cfg.Mappings)
                            {
                                if (string.IsNullOrWhiteSpace(kv.Key) || kv.Value == null) continue;
                                if (!string.IsNullOrWhiteSpace(cfg.DefaultBlockPath) &&
                                    !Path.IsPathRooted(kv.Value.BlockFilePath))
                                {
                                    kv.Value.BlockFilePath = Path.Combine(
                                        asmDir, cfg.DefaultBlockPath, kv.Value.BlockFilePath);
                                }
                                map[kv.Key.Trim()] = kv.Value;
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"WARN: Error loading blocks_mapping.json: {ex.Message}");
            }

            return map;
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Carregamento de mapeamento de layers (highway → layer CAD)
        // ──────────────────────────────────────────────────────────────────────────

        private static Dictionary<string, LayerStyle> LoadHighwayLayerMap()
        {
            var map = new Dictionary<string, LayerStyle>(StringComparer.OrdinalIgnoreCase)
            {
                ["motorway"]     = new LayerStyle { Layer = "SISRUA_OSM_MOTORWAY",    Aci = 1   },
                ["trunk"]        = new LayerStyle { Layer = "SISRUA_OSM_TRUNK",        Aci = 2   },
                ["primary"]      = new LayerStyle { Layer = "SISRUA_OSM_PRIMARY",      Aci = 3   },
                ["secondary"]    = new LayerStyle { Layer = "SISRUA_OSM_SECONDARY",    Aci = 4   },
                ["tertiary"]     = new LayerStyle { Layer = "SISRUA_OSM_TERTIARY",     Aci = 5   },
                ["residential"]  = new LayerStyle { Layer = "SISRUA_OSM_RESIDENTIAL",  Aci = 7   },
                ["service"]      = new LayerStyle { Layer = "SISRUA_OSM_SERVICE",      Aci = 8   },
                ["unclassified"] = new LayerStyle { Layer = "SISRUA_OSM_UNCLASSIFIED", Aci = 9   },
                ["living_street"]= new LayerStyle { Layer = "SISRUA_OSM_LIVING",       Aci = 30  },
                ["footway"]      = new LayerStyle { Layer = "SISRUA_OSM_PEDESTRIAN",   Aci = 140 },
                ["path"]         = new LayerStyle { Layer = "SISRUA_OSM_PATH",         Aci = 141 },
                ["cycleway"]     = new LayerStyle { Layer = "SISRUA_OSM_CYCLE",        Aci = 150 },
            };

            try
            {
                string asmDir = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                if (!string.IsNullOrWhiteSpace(asmDir))
                {
                    string cfgPath = Path.Combine(asmDir, "Resources", "layers.json");
                    if (File.Exists(cfgPath))
                    {
                        string text = File.ReadAllText(cfgPath);
                        var cfg = JsonSerializer.Deserialize<LayersConfig>(text, _jsonOptions);
                        if (cfg?.Highway != null)
                        {
                            foreach (var kv in cfg.Highway)
                            {
                                if (string.IsNullOrWhiteSpace(kv.Key) || kv.Value == null) continue;
                                map[kv.Key.Trim()] = kv.Value;
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Log($"WARN: Error loading layers.json: {ex.Message}");
            }

            return map;
        }

        // ──────────────────────────────────────────────────────────────────────────
        // Resolução de layer/ACI para uma feature
        // ──────────────────────────────────────────────────────────────────────────

        private static (string layerName, short? aci) GetLayerStyleForFeature(Core.DTOs.CadFeatureDto f)
        {
            if (f == null) return ("SISRUA_VIAS", null);

            string layerName = string.IsNullOrWhiteSpace(f.Layer) ? "SISRUA_VIAS" : f.Layer.Trim();
            string highway = f.Highway?.Trim();

            if (!string.IsNullOrWhiteSpace(highway))
            {
                if (_highwayLayerMap.Value.TryGetValue(highway, out LayerStyle style) && style != null)
                {
                    if (!string.IsNullOrWhiteSpace(style.Layer)) layerName = style.Layer.Trim();
                    return (layerName, style.Aci);
                }

                if (layerName.Equals("SISRUA_OSM_VIAS", StringComparison.OrdinalIgnoreCase))
                {
                    return ("SISRUA_OSM_OUTROS", (short?)6);
                }
            }

            return (layerName, null);
        }
    }
}
