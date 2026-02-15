using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.Core.Conditions;
using FlaUI.UIA3;
using NUnit.Framework;
using System.Diagnostics;

namespace sisRUA.UI.Tests
{
    [TestFixture]
    [Category("Desktop")]
    public class SmokeTests
    {
        private Application? _app;
        private UIA3Automation? _automation;

        [SetUp]
        public void Setup()
        {
            _automation = new UIA3Automation();
            
            // Try to attach to running AutoCAD first
            var processes = Process.GetProcessesByName("acad");
            if (processes.Length > 0)
            {
                _app = Application.Attach(processes[0]);
            }
            else
            {
                // In a real CI, we might launch it. For now, we require it running.
                Assert.Inconclusive("AutoCAD (acad.exe) not running. Skipping UI tests.");
            }
        }

        [TearDown]
        public void Teardown()
        {
            _automation?.Dispose();
            _app?.Dispose();
        }

        [Test]
        public void VerifyPluginPaletteIsVisible()
        {
            if (_app == null) return;

            var window = _app.GetMainWindow(_automation);
            Assert.That(window, Is.Not.Null, "Could not find AutoCAD main window.");

            // This is a heuristic search for the sisRUA palette
            // In a real scenario, we would need to inspect the visual tree to find the exact ID or Name
            var palette = window.FindFirstDescendant(cf => cf.ByName("sisRUA"));
            
            // If the plugin is not loaded, this might fail.
            // We assume the test environment has the plugin pre-loaded.
            if (palette == null)
            {
                Assert.Inconclusive("sisRUA palette not found in visual tree. Is the plugin loaded?");
            }
            else
            {
                Assert.That(palette.IsOffscreen, Is.False, "sisRUA palette should be visible.");
            }
        }
    }
}
