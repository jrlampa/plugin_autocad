Feature: Plugin Startup
    As a CAD Designer
    I want the sisRUA plugin to load successfully in AutoCAD
    So that I can access the urban design tools

@desktop
Scenario: User opens sisRUA palette
    Given AutoCAD 2024 is running
    And the sisRUA plugin is loaded
    When I execute the command "SISRUA_HOME"
    Then the "sisRUA" palette should be visible
    And the "STATUS: ONLINE" indicator should be green

@desktop
Scenario: Import GeoJSON
    Given the sisRUA palette is open
    When I click "Importar GeoJSON"
    And I select the file "sample_neighborhood.geojson"
    Then I should see "Importação Concluída" notification
    And the model space should contain 150 new entities
