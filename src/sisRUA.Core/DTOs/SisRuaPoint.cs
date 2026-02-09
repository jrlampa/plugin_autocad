namespace sisRUA.Core.DTOs
{
    public struct SisRuaPoint
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }

        public SisRuaPoint(double x, double y, double z = 0)
        {
            X = x; Y = y; Z = z;
        }
    }
}
