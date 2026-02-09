using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using sisRUA.Core.DTOs;

namespace sisRUA.Engine
{
    public class MockEngine : IDrawingEngine
    {
        public List<string> Operations { get; private set; } = new List<string>();
        public Dictionary<string, int> BlockCounts { get; private set; } = new Dictionary<string, int>();

        public void SaveProject(string projectId, string projectName, string crs, IEnumerable<CadFeatureDto> features)
        {
            Operations.Add($"SaveProject: {projectId}");
        }

        public void ClearModelSpace()
        {
            Operations.Add("ClearModelSpace");
        }

        public void EnsureLayer(string layerName, short colorIndex)
        {
            Operations.Add($"EnsureLayer: {layerName} ({colorIndex})");
        }

        public void InsertBlock(string blockName, SisRuaPoint position, double rotation, double scale, string layerName, Dictionary<string, string> metadata = null)
        {
            Operations.Add($"InsertBlock: {blockName} at {position} on {layerName} (meta: {metadata?.Count ?? 0})");
            if (!BlockCounts.ContainsKey(blockName)) BlockCounts[blockName] = 0;
            BlockCounts[blockName]++;
        }

        public void DrawLine(SisRuaPoint start, SisRuaPoint end, string layerName, Dictionary<string, string> metadata = null)
        {
             Operations.Add($"DrawLine: {start}->{end} on {layerName} (meta: {metadata?.Count ?? 0})");
        }

        public void DrawPolyline(IEnumerable<SisRuaPoint> points, string layerName, double? constantWidth, double? elevation, string color, Dictionary<string, string> metadata = null)
        {
            Operations.Add($"DrawPolyline: {layerName} (meta: {metadata?.Count ?? 0})");
        }

        public void WriteMessage(string message)
        {
            // No-op or Console.WriteLine for tests
        }
    }
}
