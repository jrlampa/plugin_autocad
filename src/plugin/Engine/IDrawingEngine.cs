using System.Collections.Generic;
using Autodesk.AutoCAD.Geometry;

namespace sisRUA.Engine
{
    /// <summary>
    /// Abstraction for drawing operations to facilitate testing without AutoCAD.
    /// </summary>
    public interface IDrawingEngine
    {
        void SaveProject(string projectId, string projectName, string crs, IEnumerable<object> features); // Abstracted features
        void ClearModelSpace();
        void EnsureLayer(string layerName, short colorIndex);
        void InsertBlock(string blockName, Point3d position, double rotation, double scale, string layerName);
        void DrawLine(Point3d start, Point3d end, string layerName);
        void WriteMessage(string message);
    }
}
