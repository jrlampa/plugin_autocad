using System;
using System.Collections.Generic;
using System.Linq;
using System.Security.Cryptography;
using System.Text;

namespace sisRUA
{
    /// <summary>
    /// Classe auxiliar para operações de limpeza e otimização de geometria (CadFeatures).
    /// </summary>
    public static class GeometryCleaner
    {
        private static string GetPolylineHash(CadFeature polylineFeature)
        {
            if (polylineFeature?.CoordsXy == null || !polylineFeature.CoordsXy.Any())
            {
                return null;
            }

            // Normaliza a polyline para garantir que geometrias idênticas tenham o mesmo hash
            // Ex: sort de vértices ou sempre começar do menor X,Y
            // Para simplicidade inicial, vamos usar a representação JSON dos pontos ordenados
            // e os atributos que a definem.
            var orderedPoints = polylineFeature.CoordsXy
                .SelectMany(p => p) // Flatten List<List<double>> to IEnumerable<double>
                .OrderBy(d => d) // Order all coordinates
                .ToList();
            
            var uniqueString = $"{polylineFeature.Layer}|{polylineFeature.Name}|{polylineFeature.Highway}|{polylineFeature.WidthMeters}|{JsonSerializer.Serialize(orderedPoints)}";

            using (SHA256 sha256Hash = SHA256.Create())
            {
                byte[] bytes = sha256Hash.ComputeHash(Encoding.UTF8.GetBytes(uniqueString));
                StringBuilder builder = new StringBuilder();
                for (int i = 0; i < bytes.Length; i++)
                {
                    builder.Append(bytes[i].ToString("x2"));
                }
                return builder.ToString();
            }
        }

        /// <summary>
        /// Remove CadFeatures do tipo Polyline que são duplicatas exatas.
        /// Uma duplicata é definida por ter a mesma geometria (vértices) e atributos-chave (Layer, Name, Highway, WidthMeters).
        /// </summary>
        /// <param name="features">Lista de CadFeatures a serem processados.</param>
        /// <returns>Uma nova lista de CadFeatures sem duplicatas de Polyline.</returns>
        public static IEnumerable<CadFeature> RemoveDuplicatePolylines(IEnumerable<CadFeature> features)
        {
            if (features == null || !features.Any())
            {
                return Enumerable.Empty<CadFeature>();
            }

            // Usamos um HashSet para rastrear hashes de polylines já adicionadas
            HashSet<string> seenHashes = new HashSet<string>();
            List<CadFeature> uniqueFeatures = new List<CadFeature>();

            foreach (var feature in features)
            {
                if (feature.FeatureType == CadFeatureType.Polyline)
                {
                    string polylineHash = GetPolylineHash(feature);
                    if (polylineHash != null && !seenHashes.Contains(polylineHash))
                    {
                        seenHashes.Add(polylineHash);
                        uniqueFeatures.Add(feature);
                    }
                    else if (polylineHash == null)
                    {
                        // Se o hash for nulo (polyline vazia/inválida), adiciona se não for uma "duplicata vazia"
                        // ou considera como não única se houver muitas. Para simplificação,
                        // polylines "nulas" não são adicionadas se já tivermos visto uma.
                        // Melhor seria um filtro anterior para polylines válidas.
                        // Para este método, se o hash é null, consideramos que a feature é "inválida" para ser única por hash.
                        // Mas ainda queremos manter as válidas não-polyline.
                    }
                }
                else
                {
                    // Mantém features que não são polylines (ex: pontos/blocos)
                    uniqueFeatures.Add(feature);
                }
            }
            return uniqueFeatures;
        }

        // Métodos placeholder para MergeContiguousPolylines e SimplifyPolyline
        public static IEnumerable<CadFeature> MergeContiguousPolylines(IEnumerable<CadFeature> features)
        {
            if (features == null || !features.Any())
            {
                return Enumerable.Empty<CadFeature>();
            }

            var polylineFeatures = features.Where(f => f.FeatureType == CadFeatureType.Polyline).ToList();
            var otherFeatures = features.Where(f => f.FeatureType != CadFeatureType.Polyline).ToList();

            // Group polylines by key attributes to only merge similar ones
            var groupedPolylines = polylineFeatures
                .GroupBy(f => $"{f.Layer}|{f.Name}|{f.Highway}|{f.WidthMeters}")
                .ToDictionary(g => g.Key, g => g.ToList());

            List<CadFeature> mergedPolylines = new List<CadFeature>();

            foreach (var group in groupedPolylines.Values)
            {
                var currentGroupPolylines = new List<CadFeature>(group);
                bool mergedSomethingInIteration;
                do
                {
                    mergedSomethingInIteration = false;
                    for (int i = 0; i < currentGroupPolylines.Count; i++)
                    {
                        for (int j = i + 1; j < currentGroupPolylines.Count; j++)
                        {
                            var poly1 = currentGroupPolylines[i];
                            var poly2 = currentGroupPolylines[j];

                            if (poly1.CoordsXy == null || poly2.CoordsXy == null) continue;

                            // Get start and end points of both polylines
                            var poly1Start = poly1.CoordsXy.First();
                            var poly1End = poly1.CoordsXy.Last();
                            var poly2Start = poly2.CoordsXy.First();
                            var poly2End = poly2.CoordsXy.Last();

                            List<List<double>> newCoords = null;

                            // Check for contiguity (end of poly1 to start of poly2, or vice versa)
                            if (ArePointsEqual(poly1End, poly2Start))
                            {
                                newCoords = poly1.CoordsXy.Concat(poly2.CoordsXy.Skip(1)).ToList();
                            }
                            else if (ArePointsEqual(poly2End, poly1Start))
                            {
                                newCoords = poly2.CoordsXy.Concat(poly1.CoordsXy.Skip(1)).ToList();
                            }
                            else if (ArePointsEqual(poly1Start, poly2Start))
                            {
                                // Reverse poly1 and then merge
                                var reversedPoly1Coords = new List<List<double>>(poly1.CoordsXy);
                                reversedPoly1Coords.Reverse();
                                newCoords = reversedPoly1Coords.Concat(poly2.CoordsXy.Skip(1)).ToList();
                            }
                            else if (ArePointsEqual(poly1End, poly2End))
                            {
                                // Reverse poly2 and then merge
                                var reversedPoly2Coords = new List<List<double>>(poly2.CoordsXy);
                                reversedPoly2Coords.Reverse();
                                newCoords = poly1.CoordsXy.Concat(reversedPoly2Coords.Skip(1)).ToList();
                            }

                            if (newCoords != null)
                            {
                                // Create a new merged CadFeature
                                var mergedPoly = new CadFeature
                                {
                                    FeatureType = CadFeatureType.Polyline,
                                    Layer = poly1.Layer,
                                    Name = poly1.Name,
                                    Highway = poly1.Highway,
                                    WidthMeters = poly1.WidthMeters,
                                    CoordsXy = newCoords
                                };

                                // Remove original polylines and add the merged one
                                currentGroupPolylines.RemoveAt(j); // Remove j first as it's higher index
                                currentGroupPolylines.RemoveAt(i);
                                currentGroupPolylines.Add(mergedPoly);
                                mergedSomethingInIteration = true;
                                break; // Restart inner loop as collection changed
                            }
                        }
                        if (mergedSomethingInIteration) break; // Restart outer loop as collection changed
                    }
                } while (mergedSomethingInIteration);

                mergedPolylines.AddRange(currentGroupPolylines);
            }

            otherFeatures.AddRange(mergedPolylines);
            return otherFeatures;
        }

        private static bool ArePointsEqual(List<double> p1, List<double> p2, double tolerance = 1e-6)
        {
            if (p1 == null || p2 == null || p1.Count < 2 || p2.Count < 2) return false;
            return Math.Abs(p1[0] - p2[0]) < tolerance && Math.Abs(p1[1] - p2[1]) < tolerance;
        }

        }

        // Douglas-Peucker algorithm implementation
        private static List<List<double>> SimplifyPolyline(List<List<double>> points, double tolerance)
        {
            if (points == null || points.Count < 3) return points;

            int first = 0;
            int last = points.Count - 1;
            List<int> pointIndexesToKeep = new List<int>();

            // Add the first and last points to the list of points to keep
            pointIndexesToKeep.Add(first);
            pointIndexesToKeep.Add(last);

            // The algorithm is recursive, so we need a stack to manage segments
            Stack<int[]> stack = new Stack<int[]>();
            stack.Push(new int[] { first, last });

            while (stack.Count > 0)
            {
                int[] currentSegment = stack.Pop();
                first = currentSegment[0];
                last = currentSegment[1];

                double maxDistance = 0;
                int index = 0;

                // Find the point with the maximum distance from the segment (first, last)
                for (int i = first + 1; i < last; i++)
                {
                    double distance = PerpendicularDistance(points[i], points[first], points[last]);
                    if (distance > maxDistance)
                    {
                        maxDistance = distance;
                        index = i;
                    }
                }

                // If max distance is greater than tolerance, recursively simplify the two new segments
                if (maxDistance > tolerance)
                {
                    pointIndexesToKeep.Add(index);
                    stack.Push(new int[] { first, index });
                    stack.Push(new int[] { index, last });
                }
            }

            // Reconstruct the simplified polyline from the kept points
            return pointIndexesToKeep
                .OrderBy(i => i)
                .Select(i => points[i])
                .ToList();
        }

        // Calculate perpendicular distance from a point to a line segment
        private static double PerpendicularDistance(List<double> p, List<double> lineStart, List<double> lineEnd)
        {
            double dx = lineEnd[0] - lineStart[0];
            double dy = lineEnd[1] - lineStart[1];

            // If the line segment is a point
            if (dx == 0 && dy == 0)
            {
                return Math.Sqrt(Math.Pow(p[0] - lineStart[0], 2) + Math.Pow(p[1] - lineStart[1], 2));
            }

            // Calculate the t value for the closest point on the line
            double t = ((p[0] - lineStart[0]) * dx + (p[1] - lineStart[1]) * dy) / (dx * dx + dy * dy);

            // Clamp t to the segment (0.0 to 1.0)
            t = Math.Max(0, Math.Min(1, t));

            // Closest point on the segment
            double closestX = lineStart[0] + t * dx;
            double closestY = lineStart[1] + t * dy;

            // Distance from p to the closest point
            return Math.Sqrt(Math.Pow(p[0] - closestX, 2) + Math.Pow(p[1] - closestY, 2));
        }

        /// <summary>
        /// Simplifica CadFeatures do tipo Polyline usando o algoritmo Douglas-Peucker.
        /// </summary>
        /// <param name="features">Lista de CadFeatures a serem processados.</param>
        /// <param name="tolerance">A tolerância para a simplificação (distância máxima permitida de um vértice à linha simplificada).</param>
        /// <returns>Uma nova lista de CadFeatures com polylines simplificadas.</returns>
        public static IEnumerable<CadFeature> SimplifyPolylines(IEnumerable<CadFeature> features, double tolerance)
        {
            if (features == null || !features.Any())
            {
                return Enumerable.Empty<CadFeature>();
            }

            List<CadFeature> simplifiedFeatures = new List<CadFeature>();

            foreach (var feature in features)
            {
                if (feature.FeatureType == CadFeatureType.Polyline && feature.CoordsXy != null && feature.CoordsXy.Count > 2)
                {
                    // Convert original points to a simplified list
                    var simplifiedCoords = SimplifyPolyline(feature.CoordsXy, tolerance);

                    // Create a new CadFeature for the simplified polyline
                    var simplifiedPolyline = new CadFeature
                    {
                        FeatureType = CadFeatureType.Polyline,
                        Layer = feature.Layer,
                        Name = feature.Name,
                        Highway = feature.Highway,
                        WidthMeters = feature.WidthMeters,
                        CoordsXy = simplifiedCoords
                    };
                    simplifiedFeatures.Add(simplifiedPolyline);
                }
                else
                {
                    // Add non-polylines or polylines that don't need simplification directly
                    simplifiedFeatures.Add(feature);
                }
            }
            return simplifiedFeatures;
        }
    }
}
