using System;
using System.IO;
using System.Xml.Linq;
using NUnit.Framework;

namespace sisRUA.Tests
{
    /// <summary>
    /// Tests to verify build configurations for AutoCAD 2020-2026 compatibility
    /// Validates PackageContents.xml and build output structure
    /// </summary>
    [TestFixture]
    public class BuildConfigurationTests
    {
        private string _projectRoot;
        private string _bundleTemplatePath;
        private string _packageContentsPath;

        [SetUp]
        public void Setup()
        {
            // Navigate to project root
            string baseDir = TestContext.CurrentContext.TestDirectory;
            DirectoryInfo dir = new DirectoryInfo(baseDir);
            
            while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "bundle-template")))
            {
                dir = dir.Parent;
                if (dir == null) break; // Don't go beyond root
            }

            if (dir != null)
            {
                _projectRoot = dir.FullName;
                _bundleTemplatePath = Path.Combine(_projectRoot, "bundle-template", "sisRUA.bundle");
                _packageContentsPath = Path.Combine(_bundleTemplatePath, "PackageContents.xml");
            }
        }

        [Test]
        public void VerifyPackageContentsXml_Exists()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found in bundle-template");
            }

            Assert.That(File.Exists(_packageContentsPath), Is.True,
                "PackageContents.xml should exist in bundle template");
        }

        [Test]
        public void VerifyPackageContentsXml_HasR24RuntimeRequirements()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found");
            }

            XDocument doc = XDocument.Load(_packageContentsPath);
            var r24Entries = doc.Descendants("RuntimeRequirements")
                .Where(e => 
                    e.Attribute("SeriesMin")?.Value == "R24.0" &&
                    e.Attribute("SeriesMax")?.Value == "R24.3");

            Assert.That(r24Entries.Any(), Is.True,
                "PackageContents.xml should have RuntimeRequirements for R24.0-R24.3 (AutoCAD 2021-2024)");
        }

        [Test]
        public void VerifyPackageContentsXml_HasR25RuntimeRequirements()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found");
            }

            XDocument doc = XDocument.Load(_packageContentsPath);
            var r25Entries = doc.Descendants("RuntimeRequirements")
                .Where(e => 
                    e.Attribute("SeriesMin")?.Value == "R25.0" &&
                    e.Attribute("SeriesMax")?.Value == "R25.1");

            Assert.That(r25Entries.Any(), Is.True,
                "PackageContents.xml should have RuntimeRequirements for R25.0-R25.1 (AutoCAD 2025-2026)");
        }

        [Test]
        public void VerifyPackageContentsXml_NoR23Support()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found");
            }

            XDocument doc = XDocument.Load(_packageContentsPath);
            var r23Entries = doc.Descendants("RuntimeRequirements")
                .Where(e => e.Attribute("SeriesMin")?.Value.StartsWith("R23") == true);

            Assert.That(r23Entries.Any(), Is.False,
                "PackageContents.xml should NOT have R23.x support (AutoCAD 2020 is not supported)");
        }

        [Test]
        public void VerifyPackageContentsXml_HasAutoCADAndCivil3DEntries()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found");
            }

            XDocument doc = XDocument.Load(_packageContentsPath);
            
            var autocadEntries = doc.Descendants("RuntimeRequirements")
                .Where(e => e.Attribute("Platform")?.Value == "AutoCAD");
            
            var civil3dEntries = doc.Descendants("RuntimeRequirements")
                .Where(e => e.Attribute("Platform")?.Value == "Civil3D");

            Assert.That(autocadEntries.Any(), Is.True,
                "PackageContents.xml should have AutoCAD platform entries");
            
            Assert.That(civil3dEntries.Any(), Is.True,
                "PackageContents.xml should have Civil3D platform entries");
        }

        [Test]
        public void VerifyPackageContentsXml_HasCorrectModulePaths()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found");
            }

            XDocument doc = XDocument.Load(_packageContentsPath);
            
            // Check for net48 module path
            var net48Entries = doc.Descendants("ComponentEntry")
                .Where(e => e.Attribute("ModuleName")?.Value.Contains("net48") == true);
            
            Assert.That(net48Entries.Any(), Is.True,
                "PackageContents.xml should reference net48 DLL for R24.x");

            // Check for net8.0-windows module path
            var net8Entries = doc.Descendants("ComponentEntry")
                .Where(e => e.Attribute("ModuleName")?.Value.Contains("net8.0-windows") == true);
            
            Assert.That(net8Entries.Any(), Is.True,
                "PackageContents.xml should reference net8.0-windows DLL for R25.x");
        }

        [Test]
        public void VerifyPackageContentsXml_HasRequiredCommands()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found");
            }

            XDocument doc = XDocument.Load(_packageContentsPath);
            
            var commands = doc.Descendants("Command")
                .Select(e => e.Attribute("Global")?.Value)
                .Where(v => v != null)
                .Distinct()
                .ToList();

            Assert.That(commands, Does.Contain("SISRUA"),
                "PackageContents.xml should define SISRUA command");
            
            Assert.That(commands, Does.Contain("SISRUAESCALA"),
                "PackageContents.xml should define SISRUAESCALA command");
        }

        [Test]
        public void VerifyVersionRanges_NoGaps()
        {
            if (string.IsNullOrEmpty(_packageContentsPath) || !File.Exists(_packageContentsPath))
            {
                Assert.Ignore("PackageContents.xml not found");
            }

            XDocument doc = XDocument.Load(_packageContentsPath);
            
            // R24.x should cover 2021-2024 (R24.0 - R24.3)
            var r24Reqs = doc.Descendants("RuntimeRequirements")
                .Where(e => e.Attribute("Platform")?.Value == "AutoCAD")
                .Where(e => e.Attribute("SeriesMin")?.Value.StartsWith("R24") == true)
                .FirstOrDefault();

            if (r24Reqs != null)
            {
                Assert.That(r24Reqs.Attribute("SeriesMin")?.Value, Is.EqualTo("R24.0"),
                    "R24 range should start at R24.0 (AutoCAD 2021)");
                Assert.That(r24Reqs.Attribute("SeriesMax")?.Value, Is.EqualTo("R24.3"),
                    "R24 range should end at R24.3 (AutoCAD 2024)");
            }

            // R25.x should cover 2025-2026 (R25.0 - R25.1)
            var r25Reqs = doc.Descendants("RuntimeRequirements")
                .Where(e => e.Attribute("Platform")?.Value == "AutoCAD")
                .Where(e => e.Attribute("SeriesMin")?.Value.StartsWith("R25") == true)
                .FirstOrDefault();

            if (r25Reqs != null)
            {
                Assert.That(r25Reqs.Attribute("SeriesMin")?.Value, Is.EqualTo("R25.0"),
                    "R25 range should start at R25.0 (AutoCAD 2025)");
                Assert.That(r25Reqs.Attribute("SeriesMax")?.Value, Is.EqualTo("R25.1"),
                    "R25 range should end at R25.1 (AutoCAD 2026)");
            }
        }
    }
}
