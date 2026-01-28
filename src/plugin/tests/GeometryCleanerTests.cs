using System;
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;

namespace sisRUA.Tests
{
    [TestFixture]
    public class GeometryCleanerTests
    {
        // Helper to create a simple CadFeature Polyline
        private CadFeature CreatePolylineFeature(string layer, string name, List<List<double>> coords)
        {
            return new CadFeature
            {
                FeatureType = CadFeatureType.Polyline,
                Layer = layer,
                Name = name,
                CoordsXy = coords
            };
        }

        // Helper to create a simple CadFeature Point (should not be affected by polyline cleaning)
        private CadFeature CreatePointFeature(string layer, string name, List<double> insertionPoint)
        {
            return new CadFeature
            {
                FeatureType = CadFeatureType.Point,
                Layer = layer,
                Name = name,
                InsertionPointXy = insertionPoint,
                BlockName = "TEST_BLOCK"
            };
        }

        #region TestRemoveDuplicatePolylines

        [Test]
        public void TestRemoveDuplicatePolylines_NoDuplicates()
        {
            var features = new List<CadFeature>
            {
                CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } }),
                CreatePolylineFeature("L1", "P2", new List<List<double>> { new List<double> { 2, 2 }, new List<double> { 3, 3 } })
            };

            var cleaned = GeometryCleaner.RemoveDuplicatePolylines(features);

            Assert.That(cleaned.Count(), Is.EqualTo(2));
            CollectionAssert.AreEquivalent(features, cleaned);
        }

        [Test]
        public void TestRemoveDuplicatePolylines_WithDuplicates()
        {
            var p1 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } });
            var features = new List<CadFeature>
            {
                p1,
                p1, // Duplicate
                CreatePolylineFeature("L1", "P2", new List<List<double>> { new List<double> { 2, 2 }, new List<double> { 3, 3 } }),
                CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } }) // Duplicate
            };

            var cleaned = GeometryCleaner.RemoveDuplicatePolylines(features);

            Assert.That(cleaned.Count(), Is.EqualTo(2));
            Assert.That(cleaned.Any(f => f.Name == "P1"), Is.True);
            Assert.That(cleaned.Any(f => f.Name == "P2"), Is.True);
            Assert.That(cleaned.Count(f => f.Name == "P1"), Is.EqualTo(1));
        }

        [Test]
        public void TestRemoveDuplicatePolylines_MixedFeatures()
        {
            var p1 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } });
            var b1 = CreatePointFeature("L_BLOCK", "B1", new List<double> { 10, 10 });

            var features = new List<CadFeature>
            {
                p1,
                p1, // Duplicate polyline
                b1,
                CreatePolylineFeature("L1", "P2", new List<List<double>> { new List<double> { 2, 2 }, new List<double> { 3, 3 } }),
                b1 // Duplicate point feature - should still be kept since only polylines are hashed
            };

            var cleaned = GeometryCleaner.RemoveDuplicatePolylines(features);

            // Expect 2 unique polylines + 2 point features (duplicates of non-polylines are not removed by this method)
            Assert.That(cleaned.Count(), Is.EqualTo(4));
            Assert.That(cleaned.Count(f => f.FeatureType == CadFeatureType.Polyline), Is.EqualTo(2));
            Assert.That(cleaned.Count(f => f.FeatureType == CadFeatureType.Point), Is.EqualTo(2));
        }

        #endregion

        #region TestMergeContiguousPolylines

        [Test]
        public void TestMergeContiguousPolylines_NoMergePossible()
        {
            var features = new List<CadFeature>
            {
                CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } }),
                CreatePolylineFeature("L1", "P2", new List<List<double>> { new List<double> { 2, 2 }, new List<double> { 3, 3 } })
            };

            var merged = GeometryCleaner.MergeContiguousPolylines(features);

            Assert.That(merged.Count(), Is.EqualTo(2));
            CollectionAssert.AreEquivalent(features, merged);
        }

        [Test]
        public void TestMergeContiguousPolylines_SimpleMerge()
        {
            var p1 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } });
            var p2 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 1, 1 }, new List<double> { 2, 2 } });
            var features = new List<CadFeature> { p1, p2 };

            var merged = GeometryCleaner.MergeContiguousPolylines(features);

            Assert.That(merged.Count(), Is.EqualTo(1));
            var resultPoly = merged.First();
            Assert.That(resultPoly.CoordsXy.Count, Is.EqualTo(3));
            Assert.That(resultPoly.CoordsXy[0][0], Is.EqualTo(0));
            Assert.That(resultPoly.CoordsXy[2][0], Is.EqualTo(2));
        }
        
        [Test]
        public void TestMergeContiguousPolylines_MultipleMerges()
        {
            var p1 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } });
            var p2 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 1, 1 }, new List<double> { 2, 2 } });
            var p3 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 2, 2 }, new List<double> { 3, 3 } });
            var features = new List<CadFeature> { p1, p2, p3 };

            var merged = GeometryCleaner.MergeContiguousPolylines(features);

            Assert.That(merged.Count(), Is.EqualTo(1));
            var resultPoly = merged.First();
            Assert.That(resultPoly.CoordsXy.Count, Is.EqualTo(4));
            Assert.That(resultPoly.CoordsXy[0][0], Is.EqualTo(0));
            Assert.That(resultPoly.CoordsXy[3][0], Is.EqualTo(3));
        }

        [Test]
        public void TestMergeContiguousPolylines_ReverseOrderMerge()
        {
            var p1 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } });
            var p2 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 2, 2 }, new List<double> { 1, 1 } }); // p2's end connects to p1's end
            var features = new List<CadFeature> { p1, p2 };

            var merged = GeometryCleaner.MergeContiguousPolylines(features);

            Assert.That(merged.Count(), Is.EqualTo(1));
            var resultPoly = merged.First();
            Assert.That(resultPoly.CoordsXy.Count, Is.EqualTo(3));
            Assert.That(resultPoly.CoordsXy[0][0], Is.EqualTo(0)); // Should be 0,0 - 1,1 - 2,2
            Assert.That(resultPoly.CoordsXy[2][0], Is.EqualTo(2));
        }

        [Test]
        public void TestMergeContiguousPolylines_MixedFeatures()
        {
            var p1 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } });
            var p2 = CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 1, 1 }, new List<double> { 2, 2 } });
            var b1 = CreatePointFeature("L_BLOCK", "B1", new List<double> { 10, 10 });
            var features = new List<CadFeature> { p1, p2, b1 };

            var merged = GeometryCleaner.MergeContiguousPolylines(features);

            Assert.That(merged.Count(), Is.EqualTo(2)); // One merged polyline, one point feature
            Assert.That(merged.Any(f => f.FeatureType == CadFeatureType.Polyline), Is.True);
            Assert.That(merged.Any(f => f.FeatureType == CadFeatureType.Point), Is.True);
        }

        #endregion

        #region TestSimplifyPolylines

        [Test]
        public void TestSimplifyPolylines_NoSimplificationNeeded()
        {
            var features = new List<CadFeature>
            {
                CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 1, 1 } }),
                CreatePolylineFeature("L1", "P2", new List<List<double>> { new List<double> { 2, 2 }, new List<double> { 3, 3 } })
            };

            var simplified = GeometryCleaner.SimplifyPolylines(features, 0.1);

            Assert.That(simplified.Count(), Is.EqualTo(2));
            CollectionAssert.AreEquivalent(features, simplified); // For simple polylines, should be the same
        }

        [Test]
        public void TestSimplifyPolylines_SimpleSimplification()
        {
            var features = new List<CadFeature>
            {
                CreatePolylineFeature("L1", "P1", new List<List<double>> { new List<double> { 0, 0 }, new List<double> { 0.5, 0.1 }, new List<double> { 1, 0 } })
            };

            var simplified = GeometryCleaner.SimplifyPolylines(features, 0.05); // Tolerance that should remove 0.5,0.1

            Assert.That(simplified.Count(), Is.EqualTo(1));
            var resultPoly = simplified.First();
            Assert.That(resultPoly.CoordsXy.Count, Is.EqualTo(2)); // Should be [0,0], [1,0]
            Assert.That(resultPoly.CoordsXy[0][0], Is.EqualTo(0));
            Assert.That(resultPoly.CoordsXy[1][0], Is.EqualTo(1));
        }

        [Test]
        public void TestSimplifyPolylines_ComplexSimplification()
        {
            var features = new List<CadFeature>
            {
                CreatePolylineFeature("L1", "P1", new List<List<double>> {
                    new List<double> { 0, 0 },
                    new List<double> { 1, 0 },
                    new List<double> { 1.5, 0.1 }, // Can be removed
                    new List<double> { 2, 0 },
                    new List<double> { 2.5, 0.6 }, // Might be kept
                    new List<double> { 3, 0 }
                })
            };

            var simplified = GeometryCleaner.SimplifyPolylines(features, 0.2); // Tolerance

            Assert.That(simplified.Count(), Is.EqualTo(1));
            var resultPoly = simplified.First();
            // Expected number of points after simplification depends on tolerance and geometry
            // For 0.2, it might remove 1.5,0.1 and keep 2.5,0.6
            // A precise count needs to be calculated by running DP algorithm manually or having known output
            Assert.That(resultPoly.CoordsXy.Count, Is.LessThan(features.First().CoordsXy.Count));
            // Ensure start and end points are always kept
            Assert.That(resultPoly.CoordsXy.First(), Is.EqualTo(features.First().CoordsXy.First()));
            Assert.That(resultPoly.CoordsXy.Last(), Is.EqualTo(features.First().CoordsXy.Last()));
        }

        [Test]
        public void TestSimplifyPolylines_ToleranceEffect()
        {
            var points = new List<List<double>> {
                new List<double> { 0, 0 },
                new List<double> { 1, 0.1 },
                new List<double> { 2, 0 },
                new List<double> { 3, 0.5 },
                new List<double> { 4, 0 }
            };
            var feature = CreatePolylineFeature("L1", "P1", points);

            // High tolerance, expect aggressive simplification
            var simplifiedHigh = GeometryCleaner.SimplifyPolylines(new List<CadFeature>{feature}, 0.4).First();
            Assert.That(simplifiedHigh.CoordsXy.Count, Is.LessThanOrEqualTo(3)); // e.g., might be 0,0 - 3,0.5 - 4,0

            // Low tolerance, expect less simplification
            var simplifiedLow = GeometryCleaner.SimplifyPolylines(new List<CadFeature>{feature}, 0.01).First();
            Assert.That(simplifiedLow.CoordsXy.Count, Is.GreaterThan(simplifiedHigh.CoordsXy.Count));
            Assert.That(simplifiedLow.CoordsXy.Count, Is.LessThanOrEqualTo(points.Count));
        }

        #endregion
    }
}
