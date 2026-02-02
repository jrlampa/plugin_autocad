using System;
using System.Collections.Generic;
using Autodesk.AutoCAD.Geometry;

namespace sisRUA.Engine
{
    public class MockEngine : IDrawingEngine
    {
        public List<string> Operations { get; private set; } = new List<string>();
        public Dictionary<string, int> BlockCounts { get; private set; } = new Dictionary<string, int>();

        public void SaveProject(string projectId, string projectName, string crs, IEnumerable<object> features)
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

        public void InsertBlock(string blockName, Point3d position, double rotation, double scale, string layerName)
        {
            Operations.Add($"InsertBlock: {blockName} at {position} on {layerName}");
            if (!BlockCounts.ContainsKey(blockName)) BlockCounts[blockName] = 0;
            BlockCounts[blockName]++;
        }

        public void DrawLine(Point3d start, Point3d end, string layerName)
        {
             Operations.Add($"DrawLine: {start}->{end} on {layerName}");
        }

        public void WriteMessage(string message)
        {
            // No-op or Console.WriteLine for tests
            // Console.WriteLine(message); 
        }
    }
}
