using System;
using System.Collections.Generic;
using System.Data.SQLite;
using System.IO;
using System.Linq;
using NUnit.Framework; // Using NUnit as a common C# testing framework
using sisRUA;


// Assuming CadFeature, CadFeatureType, ProjectRepository are in sisRUA namespace
// For a proper test project setup, these would be referenced or included.
// For now, we'll assume direct access or mock them if necessary.

namespace sisRUA.Tests
{
    [TestFixture]
    public class ProjectRepositoryTests
    {
        private string _testDbPath;
        private ProjectRepository _repository;

        [SetUp]
        public void Setup()
        {
            // Create a temporary, file-based database for each test
            // We use file-based because the current ProjectRepository implementation
            // opens and closes connections for each operation, which wipes :memory: databases.
            _testDbPath = Path.Combine(Path.GetTempPath(), $"sisrua_test_{Guid.NewGuid():N}.db");

            // Mock or setup SisRuaPlugin.GetLocalSisRuaDir() for test context
            typeof(ProjectRepository)
                .GetField("_databasePath", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Static)
                .SetValue(null, _testDbPath);

            _repository = new ProjectRepository();
            // Ensure tables are created for the in-memory db
            // This is implicitly called by ProjectRepository constructor, but good to be explicit for clarity
            typeof(ProjectRepository)
                .GetMethod("CreateTablesIfNotExist", System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance)
                .Invoke(_repository, null);
        }

        [TearDown]
        public void Teardown()
        {
            // Close the in-memory database connection
            // For file-based, delete the temporary file
            if (_testDbPath != ":memory:" && File.Exists(_testDbPath))
            {
                File.Delete(_testDbPath);
            }
        }

        [Test]
        public void TestCreateTablesIfNotExist()
        {
            // Test setup creates tables implicitly. Just verify they exist.
            using (var connection = new SQLiteConnection($"Data Source={_testDbPath};Version=3;"))
            {
                connection.Open();
                using (var command = connection.CreateCommand())
                {
                    command.CommandText = "SELECT name FROM sqlite_master WHERE type='table' AND name='Projects';";
                    Assert.That(command.ExecuteScalar(), Is.EqualTo("Projects"), "Projects table should exist.");

                    command.CommandText = "SELECT name FROM sqlite_master WHERE type='table' AND name='CadFeatures';";
                    Assert.That(command.ExecuteScalar(), Is.EqualTo("CadFeatures"), "CadFeatures table should exist.");
                }
            }
        }

        [Test]
        public void TestSaveAndLoadProject_PolylineFeatures()
        {
            string projectId = "TEST001";
            string projectName = "My Test Project";
            string crsOut = "EPSG:31984";

            var features = new List<CadFeature>
            {
                new CadFeature
                {
                    FeatureType = CadFeatureType.Polyline,
                    Layer = "ROAD",
                    Name = "Test Road",
                    Highway = "residential",
                    WidthMeters = 5.0,
                    CoordsXy = new List<List<double>> { new List<double> { 10.0, 20.0 }, new List<double> { 30.0, 40.0 } }
                },
                new CadFeature
                {
                    FeatureType = CadFeatureType.Polyline,
                    Layer = "SIDEWALK",
                    Name = "Test Sidewalk",
                    CoordsXy = new List<List<double>> { new List<double> { 11.0, 21.0 }, new List<double> { 31.0, 41.0 } }
                }
            };

            _repository.SaveProject(projectId, projectName, crsOut, features);

            var (loadedProjectName, loadedCrsOut, loadedFeatures) = _repository.LoadProject(projectId);

            Assert.That(loadedProjectName, Is.EqualTo(projectName));
            Assert.That(loadedCrsOut, Is.EqualTo(crsOut));
            Assert.That(loadedFeatures, Is.Not.Null);
            Assert.That(loadedFeatures.Count, Is.EqualTo(2));

            CadFeature loadedF0 = loadedFeatures[0];
            Assert.That(loadedF0.FeatureType, Is.EqualTo(CadFeatureType.Polyline));
            Assert.That(loadedF0.Layer, Is.EqualTo("ROAD"));
            Assert.That(loadedF0.Name, Is.EqualTo("Test Road"));
            Assert.That(loadedF0.CoordsXy.Count, Is.EqualTo(2));
            Assert.That(loadedF0.CoordsXy[0][0], Is.EqualTo(10.0));
            // Add more assertions for other properties
        }

        [Test]
        public void TestSaveAndLoadProject_PointFeatures()
        {
            string projectId = "TEST002";
            string projectName = "My Block Project";
            string crsOut = "EPSG:31984";

            var features = new List<CadFeature>
            {
                new CadFeature
                {
                    FeatureType = CadFeatureType.Point,
                    Layer = "POLE",
                    Name = "Power Pole 1",
                    InsertionPointXy = new List<double> { 100.0, 200.0 },
                    BlockName = "POSTE_GENERICO",
                    BlockFilePath = "POSTE_GENERICO.dxf",
                    Rotation = 0.5,
                    Scale = 2.0
                }
            };

            _repository.SaveProject(projectId, projectName, crsOut, features);

            var (loadedProjectName, loadedCrsOut, loadedFeatures) = _repository.LoadProject(projectId);

            Assert.That(loadedProjectName, Is.EqualTo(projectName));
            Assert.That(loadedCrsOut, Is.EqualTo(crsOut));
            Assert.That(loadedFeatures, Is.Not.Null);
            Assert.That(loadedFeatures.Count, Is.EqualTo(1));

            CadFeature loadedF0 = loadedFeatures[0];
            Assert.That(loadedF0.FeatureType, Is.EqualTo(CadFeatureType.Point));
            Assert.That(loadedF0.Layer, Is.EqualTo("POLE"));
            Assert.That(loadedF0.Name, Is.EqualTo("Power Pole 1"));
            Assert.That(loadedF0.InsertionPointXy.Count, Is.EqualTo(2));
            Assert.That(loadedF0.InsertionPointXy[0], Is.EqualTo(100.0));
            Assert.That(loadedF0.BlockName, Is.EqualTo("POSTE_GENERICO"));
            Assert.That(loadedF0.BlockFilePath, Is.EqualTo("POSTE_GENERICO.dxf"));
            Assert.That(loadedF0.Rotation, Is.EqualTo(0.5));
            Assert.That(loadedF0.Scale, Is.EqualTo(2.0));
        }

        [Test]
        public void TestListProjects()
        {
            _repository.SaveProject("PROJ001", "Project A", "EPSG:31984", new List<CadFeature>());
            _repository.SaveProject("PROJ002", "Project B", "EPSG:31984", new List<CadFeature>());

            var projects = _repository.ListProjects();

            Assert.That(projects, Is.Not.Null);
            Assert.That(projects.Count, Is.EqualTo(2));
            Assert.That(projects.Any(p => p.projectId == "PROJ001" && p.projectName == "Project A"), Is.True);
            Assert.That(projects.Any(p => p.projectId == "PROJ002" && p.projectName == "Project B"), Is.True);
        }

        [Test]
        public void TestSaveProjectUpdateExisting()
        {
            string projectId = "UPDATE001";
            string oldProjectName = "Old Name";
            string newProjectName = "New Name";

            _repository.SaveProject(projectId, oldProjectName, "EPSG:31984", new List<CadFeature> { new CadFeature { FeatureType = CadFeatureType.Polyline, CoordsXy = new List<List<double>> { new List<double> { 0.0, 0.0 }, new List<double> { 1.0, 1.0 } } } });
            _repository.SaveProject(projectId, newProjectName, "EPSG:31984", new List<CadFeature> { new CadFeature { FeatureType = CadFeatureType.Polyline, CoordsXy = new List<List<double>> { new List<double> { 2.0, 2.0 }, new List<double> { 3.0, 3.0 } } } });

            var (loadedProjectName, _, loadedFeatures) = _repository.LoadProject(projectId);
            var projects = _repository.ListProjects();

            Assert.That(loadedProjectName, Is.EqualTo(newProjectName));
            Assert.That(loadedFeatures.Count, Is.EqualTo(1));
            Assert.That(projects.Count, Is.EqualTo(1), "Should only be one project with this ID.");
        }

        [Test]
        public void TestLoadNonExistentProject()
        {
            var (projectName, crsOut, features) = _repository.LoadProject("NONEXISTENT");
            Assert.That(projectName, Is.Null);
            Assert.That(features, Is.Null); // ProjectRepository returns null for features if not found
        }
    }
}
