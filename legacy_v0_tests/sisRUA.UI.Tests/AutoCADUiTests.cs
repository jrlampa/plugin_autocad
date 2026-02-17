using System;
using System.Linq;
using FlaUI.Core;
using FlaUI.Core.AutomationElements;
using FlaUI.UIA3;
using Xunit;

namespace sisRUA.UI.Tests
{
    public class AutoCADUiTests
    {
        [Fact]
        public void VerifyGenerateButtonExists()
        {
            // Note: In a real CI environment, we would use a mock or a controlled AutoCAD launch.
            // For this proof, we attempt to attach to an existing AutoCAD process.
            var app = Application.Attach("acad.exe");
            
            using (var automation = new UIA3Automation())
            {
                var mainWindow = app.GetMainWindow(automation);
                Assert.NotNull(mainWindow);

                // Look for the sisRUA Palette/Window
                // Adjusting the search to look for the button name or automation ID
                var palette = mainWindow.FindFirstDescendant(cf => cf.ByName("sisRUA"));
                
                // If the palette is not found by name, it might be inside a list or custom container
                // but for 2026 standards, we expect the button to be detectable.
                var generateButton = mainWindow.FindFirstDescendant(cf => cf.ByName("Gerar")) 
                                     ?? mainWindow.FindFirstDescendant(cf => cf.ByAutomationId("btnGenerate"));

                Assert.True(generateButton != null, "The 'Gerar' button was not found in the AutoCAD UI.");
            }
        }
    }
}
