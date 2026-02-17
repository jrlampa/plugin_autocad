using System;
using System.IO;
using System.Linq;
using NUnit.Framework;

namespace sisRUA.Tests
{
    [TestFixture]
    public class ReleasePackageTests
    {
        private string _releasePath;

        [SetUp]
        public void Setup()
        {
            // Get root directory (3 levels up from tests/bin/Debug/net8.0-windows/)
            string baseDir = TestContext.CurrentContext.TestDirectory;
            DirectoryInfo dir = new DirectoryInfo(baseDir);
            
            // Navigate up to find the project root (where 'release' folder should be)
            while (dir != null && !Directory.Exists(Path.Combine(dir.FullName, "release")))
            {
                dir = dir.Parent;
                if (dir?.Parent == null) break; // Don't go to root drive
            }

            if (dir != null)
            {
                _releasePath = Path.Combine(dir.FullName, "release", "sisRUA.bundle");
            }
        }

        [Test]
        public void VerifyBundleStructure_Exists()
        {
            if (string.IsNullOrEmpty(_releasePath) || !Directory.Exists(_releasePath))
            {
                Assert.Ignore("Release bundle not found. Run build_release.cmd first.");
            }

            Assert.That(File.Exists(Path.Combine(_releasePath, "PackageContents.xml")), Is.True, "PackageContents.xml missing");
            Assert.That(Directory.Exists(Path.Combine(_releasePath, "Contents")), Is.True, "Contents folder missing");
        }

        [Test]
        public void VerifyCompatibilityDlls_Present()
        {
            if (string.IsNullOrEmpty(_releasePath) || !Directory.Exists(_releasePath))
            {
                Assert.Ignore("Release bundle not found. Skipping DLL verification.");
            }

            string contentsPath = Path.Combine(_releasePath, "Contents");
            
            string[] requiredDlls = new[]
            {
                "sisRUA_NET8.dll",
                "sisRUA_NET48_ACAD2021.dll",
                "sisRUA_NET48_ACAD2024.dll"
            };

            foreach (var dll in requiredDlls)
            {
                string dllPath = Path.Combine(contentsPath, dll);
                Assert.That(File.Exists(dllPath), Is.True, $"Critical DLL missing: {dll}");
            }
        }

        [Test]
        public void VerifyBackendExe_Present()
        {
            if (string.IsNullOrEmpty(_releasePath) || !Directory.Exists(_releasePath))
            {
                Assert.Ignore("Release bundle not found. Skipping backend verification.");
            }

            string backendPath = Path.Combine(_releasePath, "Contents", "backend", "sisrua_backend.exe");
            Assert.That(File.Exists(backendPath), Is.True, "Backend executable (sisrua_backend.exe) missing");
        }
    }
}
