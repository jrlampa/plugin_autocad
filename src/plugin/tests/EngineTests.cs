using NUnit.Framework;
using sisRUA.Engine;
using Autodesk.AutoCAD.Geometry;
using System.Collections.Generic;

namespace sisRUA.Tests
{
    [TestFixture]
    public class EngineTests
    {
        [Test]
        public void TestMockEngine_Interactions()
        {
            // Arrange
            var mock = new MockEngine();
            SisRuaCommands.Engine = mock;

            // Act - Simulating a command action
            // In a real scenario, we would call SisRuaCommands.SomeLogicMethod() 
            // but since those are mixed with static state, we demonstrate the engine usage directly here
            
            SisRuaCommands.Engine.WriteMessage("Test Message");
            SisRuaCommands.Engine.InsertBlock("POSTE", new Point3d(0,0,0), 0, 1, "0");

            // Assert
            Assert.That(mock.Operations, Does.Contain("InsertBlock: POSTE at (0,0,0) on 0"));
            Assert.That(mock.BlockCounts["POSTE"], Is.EqualTo(1));
        }
        
        [Test]
        public void TestMockEngine_SaveProject()
        {
             var mock = new MockEngine();
             mock.SaveProject("P123", "Project X", "EPSG:4326", new List<object>());
             Assert.That(mock.Operations, Does.Contain("SaveProject: P123"));
        }
    }
}
