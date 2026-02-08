using System.Collections.Generic;
using Autodesk.AutoCAD.Geometry;

namespace sisRUA.Engine
{
    /// <summary>
    /// Abstraction for drawing operations to facilitate testing without AutoCAD.
    /// </summary>
    public interface IDrawingEngine
    {
        void SaveProject(string projectId, string projectName, string crs, IEnumerable<object> features);
        void ClearModelSpace();
        void EnsureLayer(string layerName, short colorIndex);
        void InsertBlock(string blockName, SisRuaPoint position, double rotation, double scale, string layerName, Dictionary<string, string> metadata = null);
        void DrawLine(SisRuaPoint start, SisRuaPoint end, string layerName);
        void DrawPolyline(IEnumerable<SisRuaPoint> points, string layerName, double? constantWidth, double? elevation, string color, Dictionary<string, string> metadata = null);
        void WriteMessage(string message);
    }
}
