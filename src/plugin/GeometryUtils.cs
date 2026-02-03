using System;
using System.Collections.Generic;
using System.Linq;

namespace sisRUA
{
    /// <summary>
    /// Utility class for geometric calculations that are host-agnostic.
    /// </summary>
    public static class GeometryUtils
    {
        /// <summary>
        /// Calculates the total length of a polyline in meters.
        /// Assumes coordinates are in meters (UTM/SIRGAS).
        /// </summary>
        public static double CalculateLength(IEnumerable<List<double>> coords)
        {
            if (coords == null || coords.Count() < 2) return 0;

            double totalLength = 0;
            var pointList = coords.ToList();

            for (int i = 0; i < pointList.Count - 1; i++)
            {
                var p1 = pointList[i];
                var p2 = pointList[i + 1];

                if (p1.Count < 2 || p2.Count < 2) continue;

                double dx = p2[0] - p1[0];
                double dy = p2[1] - p1[1];
                
                totalLength += Math.Sqrt(dx * dx + dy * dy);
            }

            return totalLength;
        }

        /// <summary>
        /// Calculates total mileage in kilometers for a collection of CadFeatures.
        /// </summary>
        public static double CalculateTotalMileageKm(IEnumerable<CadFeature> features)
        {
            if (features == null) return 0;

            double totalMeters = 0;
            foreach (var feature in features)
            {
                if (feature.FeatureType == CadFeatureType.Polyline && feature.CoordsXy != null)
                {
                    totalMeters += CalculateLength(feature.CoordsXy);
                }
            }

            return totalMeters / 1000.0;
        }
    }
}
