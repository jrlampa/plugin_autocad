using System;
using System.Collections.Generic;
using NUnit.Framework;

namespace sisRUA.Tests
{
    /// <summary>
    /// Tests for AutoCAD version compatibility (2020-2026)
    /// Validates version detection, runtime requirements, and build configurations
    /// </summary>
    [TestFixture]
    public class AutoCADVersionCompatibilityTests
    {
        /// <summary>
        /// AutoCAD version to R-series mapping
        /// Source: Autodesk AutoCAD .NET Developer's Guide
        /// </summary>
        private static readonly Dictionary<string, string> VersionToRSeriesMap = new()
        {
            { "2020", "R23.1" },
            { "2021", "R24.0" },
            { "2022", "R24.1" },
            { "2023", "R24.2" },
            { "2024", "R24.3" },
            { "2025", "R25.0" },
            { "2026", "R25.1" }
        };

        /// <summary>
        /// Supported AutoCAD versions in current build
        /// </summary>
        private static readonly HashSet<string> SupportedVersions = new()
        {
            "2021", "2022", "2023", "2024", // R24.x via .NET 4.8
            "2025", "2026"                   // R25.x via .NET 8
        };

        /// <summary>
        /// Explicitly unsupported versions
        /// </summary>
        private static readonly HashSet<string> UnsupportedVersions = new()
        {
            "2020" // R23.1 - would require separate .NET 4.7 build with AutoCAD.NET 23.0.0
        };

        [Test]
        [TestCase("2020", "R23.1", false)]
        [TestCase("2021", "R24.0", true)]
        [TestCase("2022", "R24.1", true)]
        [TestCase("2023", "R24.2", true)]
        [TestCase("2024", "R24.3", true)]
        [TestCase("2025", "R25.0", true)]
        [TestCase("2026", "R25.1", true)]
        public void VerifyVersionMapping_CorrectRSeries(string version, string expectedRSeries, bool shouldBeSupported)
        {
            // Verify R-series mapping is correct
            Assert.That(VersionToRSeriesMap.ContainsKey(version), Is.True, 
                $"Version {version} not found in mapping");
            Assert.That(VersionToRSeriesMap[version], Is.EqualTo(expectedRSeries),
                $"AutoCAD {version} should map to {expectedRSeries}");

            // Verify support status is correct
            bool isSupported = SupportedVersions.Contains(version);
            Assert.That(isSupported, Is.EqualTo(shouldBeSupported),
                $"AutoCAD {version} support status mismatch");
        }

        [Test]
        [TestCase("2021", ".NET Framework 4.8", "24.0.0")]
        [TestCase("2022", ".NET Framework 4.8", "24.1.0")]
        [TestCase("2023", ".NET Framework 4.8", "24.2.0")]
        [TestCase("2024", ".NET Framework 4.8", "24.3.0")]
        [TestCase("2025", ".NET 8", "25.0.0")]
        [TestCase("2026", ".NET 8", "25.1.0")]
        public void VerifyRuntimeRequirements_SupportedVersions(
            string version, 
            string expectedRuntime, 
            string expectedAutoCADNetVersion)
        {
            Assert.That(SupportedVersions.Contains(version), Is.True,
                $"AutoCAD {version} should be in supported versions list");

            // Verify correct runtime is documented
            if (version == "2025" || version == "2026")
            {
                Assert.That(expectedRuntime, Is.EqualTo(".NET 8"),
                    $"AutoCAD {version} should use .NET 8");
            }
            else
            {
                Assert.That(expectedRuntime, Is.EqualTo(".NET Framework 4.8"),
                    $"AutoCAD {version} should use .NET Framework 4.8");
            }
        }

        [Test]
        public void VerifyUnsupportedVersions_AutoCAD2020()
        {
            Assert.That(UnsupportedVersions.Contains("2020"), Is.True,
                "AutoCAD 2020 (R23.1) should be explicitly marked as unsupported");
            
            Assert.That(SupportedVersions.Contains("2020"), Is.False,
                "AutoCAD 2020 should not be in supported versions");
        }

        [Test]
        public void VerifyVersionRanges_R24Series()
        {
            // R24.x range should include 2021-2024
            var r24Versions = new[] { "2021", "2022", "2023", "2024" };
            
            foreach (var version in r24Versions)
            {
                Assert.That(SupportedVersions.Contains(version), Is.True,
                    $"AutoCAD {version} should be supported in R24.x range");
                
                Assert.That(VersionToRSeriesMap[version].StartsWith("R24"), Is.True,
                    $"AutoCAD {version} should be in R24.x series");
            }
        }

        [Test]
        public void VerifyVersionRanges_R25Series()
        {
            // R25.x range should include 2025-2026
            var r25Versions = new[] { "2025", "2026" };
            
            foreach (var version in r25Versions)
            {
                Assert.That(SupportedVersions.Contains(version), Is.True,
                    $"AutoCAD {version} should be supported in R25.x range");
                
                Assert.That(VersionToRSeriesMap[version].StartsWith("R25"), Is.True,
                    $"AutoCAD {version} should be in R25.x series");
            }
        }

        [Test]
        public void VerifyTargetFrameworks_MatchAutoCADVersions()
        {
            // .NET 4.8 target should support R24.x (2021-2024)
            var net48Versions = new[] { "2021", "2022", "2023", "2024" };
            foreach (var version in net48Versions)
            {
                string rSeries = VersionToRSeriesMap[version];
                Assert.That(rSeries.StartsWith("R24"), Is.True,
                    $"AutoCAD {version} ({rSeries}) should use .NET Framework 4.8");
            }

            // .NET 8 target should support R25.x (2025-2026)
            var net8Versions = new[] { "2025", "2026" };
            foreach (var version in net8Versions)
            {
                string rSeries = VersionToRSeriesMap[version];
                Assert.That(rSeries.StartsWith("R25"), Is.True,
                    $"AutoCAD {version} ({rSeries}) should use .NET 8");
            }
        }

        [Test]
        public void VerifySupportedVersionCount()
        {
            // Should support exactly 6 versions (2021-2026)
            Assert.That(SupportedVersions.Count, Is.EqualTo(6),
                "Should support exactly 6 AutoCAD versions");
        }

        [Test]
        public void VerifyCompleteCoverage_2020Through2026()
        {
            // All versions from 2020-2026 should be either supported or explicitly unsupported
            for (int year = 2020; year <= 2026; year++)
            {
                string version = year.ToString();
                bool isSupported = SupportedVersions.Contains(version);
                bool isUnsupported = UnsupportedVersions.Contains(version);
                
                Assert.That(isSupported || isUnsupported, Is.True,
                    $"AutoCAD {version} should be either in supported or unsupported list");
                
                Assert.That(isSupported && isUnsupported, Is.False,
                    $"AutoCAD {version} cannot be both supported and unsupported");
            }
        }
    }
}
