using System.Collections.Generic;
using System.Threading.Tasks;
using sisRUA.Core.DTOs;
using Autodesk.AutoCAD.Geometry;

namespace sisRUA.Engine
{
    /// <summary>
    /// Abstraction for drawing operations to facilitate testing without AutoCAD.
    /// </summary>
    public interface IDrawingEngine
    {
        // --- High-Level Drawing ---
        Task DrawFeaturesAsync(IEnumerable<CadFeatureDto> features, string crsOut, IProcessingProgress progress);
        
        // --- Low-Level Drawing (Atomic) ---
        void EnsureLayer(string layerName, short colorIndex);
        void InsertBlock(string blockName, SisRuaPoint position, double rotation, double scale, string layerName, Dictionary<string, string> metadata = null);
        void DrawLine(SisRuaPoint start, SisRuaPoint end, string layerName, Dictionary<string, string> metadata = null);
        void DrawPolyline(IEnumerable<SisRuaPoint> points, string layerName, double? constantWidth, double? elevation, string color, Dictionary<string, string> metadata = null);
        
        // --- System & Metadata ---
        void ClearModelSpace();
        void WriteMessage(string message);
        void InjectAuditMetadata(string projectId);
        double GetScaleFactor();
        
        // --- Legacy/Compatibility ---
        void SaveProject(string projectId, string projectName, string crs, IEnumerable<CadFeatureDto> features);
    }

    public interface IProcessingProgress
    {
        bool WasCancelled { get; }
        void SetProgress(int percent);
        void UpdateScreen();
    }
}
