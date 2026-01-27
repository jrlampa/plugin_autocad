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
            // Implementação futura
            return features;
        }

        public static IEnumerable<CadFeature> SimplifyPolylines(IEnumerable<CadFeature> features, double tolerance)
        {
            // Implementação futura
            return features;
        }
    }
}
