using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Xml.Linq;
using sisRUA.Core.DTOs;

namespace sisRUA
{
    /// <summary>
    /// Executes geometry compliance and integration tests to verify the integrity of the graphic engine
    /// and optimization algorithms (GeometryCleaner).
    /// </summary>
    public static class GeometryComplianceTests
    {
        public class TestResult
        {
            public string Name { get; set; }
            public bool Passed { get; set; }
            public string Message { get; set; }
            public long DurationMs { get; set; }
        }

        public static void RunAndExport(string outputPath)
        {
            var results = new List<TestResult>();
            
            // Run Tests
            results.Add(ExecuteTest("RemoveDuplicatePolylines_ExactMatch", TestRemoveDuplicatePolylines_ExactMatch));
            results.Add(ExecuteTest("MergeContiguousPolylines_Success", TestMergeContiguousPolylines_Success));
            results.Add(ExecuteTest("SimplifyPolylines_ReductionRatio", TestSimplifyPolylines_ReductionRatio));
            results.Add(ExecuteTest("Geometry25D_Compliance", TestGeometry25D_Compliance));

            // Export to JUnit-style XML
            ExportToXml(results, outputPath);
        }

        private static TestResult ExecuteTest(string name, Func<string> testFunc)
        {
            var sw = System.Diagnostics.Stopwatch.StartNew();
            try
            {
                string message = testFunc();
                sw.Stop();
                return new TestResult { Name = name, Passed = true, Message = message, DurationMs = sw.ElapsedMilliseconds };
            }
            catch (Exception ex)
            {
                sw.Stop();
                return new TestResult { Name = name, Passed = false, Message = ex.Message, DurationMs = sw.ElapsedMilliseconds };
            }
        }

        private static string TestRemoveDuplicatePolylines_ExactMatch()
        {
            var coords = new List<List<double>> { new List<double>{0,0}, new List<double>{1,1} };
            var features = new List<CadFeatureDto>
            {
                new CadFeatureDto { FeatureType = CadFeatureDtoType.Polyline, Layer = "Road", CoordsXy = coords },
                new CadFeatureDto { FeatureType = CadFeatureDtoType.Polyline, Layer = "Road", CoordsXy = coords } // Duplicate
            };

            var clean = GeometryCleaner.RemoveDuplicatePolylines(features).ToList();
            if (clean.Count != 1) 
                throw new Exception($"Expected 1 feature, got {clean.Count}");
            
            return "Successfully removed identical polyline duplicates.";
        }

        private static string TestMergeContiguousPolylines_Success()
        {
            var features = new List<CadFeatureDto>
            {
                new CadFeatureDto { FeatureType = CadFeatureDtoType.Polyline, Layer = "Test", CoordsXy = new List<List<double>> { new List<double>{0,0}, new List<double>{10,10} } },
                new CadFeatureDto { FeatureType = CadFeatureDtoType.Polyline, Layer = "Test", CoordsXy = new List<List<double>> { new List<double>{10,10}, new List<double>{20,20} } }
            };

            var merged = GeometryCleaner.MergeContiguousPolylines(features).ToList();
            if (merged.Count != 1)
                throw new Exception($"Expected 1 merged feature, got {merged.Count}");
            
            if (merged[0].CoordsXy.Count != 3)
                throw new Exception($"Expected 3 vertices in merged polyline, got {merged[0].CoordsXy.Count}");

            return "Successfully merged contiguous polyline segments.";
        }

        private static string TestGeometry25D_Compliance()
        {
            var start = new SisRuaPoint(0, 0, 10);
            var end = new SisRuaPoint(10, 10, 20); // 3D line

            var line = CadFeatureFactory.CreateLine(start, end);
            
            if (line.StartPoint.Z != line.EndPoint.Z)
                throw new Exception($"Line is not 2.5D. Variance in Z detected: {line.StartPoint.Z} != {line.EndPoint.Z}");

            if (line.StartPoint.Z != 10)
                throw new Exception($"Line elevation incorrect. Expected 10, got {line.StartPoint.Z}");

            return "Geometry 2.5D compliance verified (strictly constant elevation).";
        }

        private static void ExportToXml(List<TestResult> results, string path)
        {
            var doc = new XDocument(
                new XElement("testsuite",
                    new XAttribute("name", "GeometryIntegritySuite"),
                    new XAttribute("tests", results.Count),
                    new XAttribute("failures", results.Count(r => !r.Passed)),
                    results.Select(r => new XElement("testcase",
                        new XAttribute("name", r.Name),
                        new XAttribute("time", r.DurationMs / 1000.0),
                        !r.Passed ? new XElement("failure", r.Message) : null,
                        r.Passed ? new XElement("system-out", r.Message) : null
                    ))
                )
            );
            
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            doc.Save(path);
        }
    }
}
