namespace sisRUA.Core.DTOs
{
    public struct SisRuaPoint
    {
        public double X { get; set; }
        public double Y { get; set; }

        /// <summary>
        /// Z coordinate. 
        /// WARNING: In 2.5D architecture, this should only be used as a constant displacement (elevation).
        /// For geometric shapes, use X and Y.
        /// </summary>
        public double Z { get; set; }

        public SisRuaPoint(double x, double y, double z = 0)
        {
            X = x; Y = y; Z = z;
        }
    }
}
