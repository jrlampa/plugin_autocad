# Test Plan for sisRUA Plugin Compatibility with AutoCAD 2021+

## Objective
To verify that the sisRUA plugin functions correctly across AutoCAD versions 2021, 2024, and 2026 after implementing version-specific .NET Framework 4.8 builds and enhanced logging.

## Test Environment
*   Clean installations of:
    *   AutoCAD 2021 (with .NET Framework 4.8)
    *   AutoCAD 2024 (with .NET Framework 4.8)
    *   AutoCAD 2026 (with .NET 8)
*   Windows 10/11 operating system.
*   Ensure WebView2 Runtime is installed on all test machines.
*   Ensure Python 3.7+ is installed (for debug mode/fallback testing).

## Test Artifacts
*   `sisRUA_NET48_ACAD2021.dll` (and corresponding .pdb)
*   `sisRUA_NET48_ACAD2024.dll` (and corresponding .pdb)
*   `sisRUA_NET8.dll` (and corresponding .pdb)
*   `sisRUA.bundle` containing all necessary DLLs and resources.
*   `sisRUA_plugin_[timestamp].log` files generated in `%LOCALAPPDATA%\sisRUA\logs`.

## Test Cases

### Pre-requisites for all tests:
1.  Build the plugin using the updated `build_release.cmd` to generate all three DLL versions.
    *   Run `build_release.cmd`. This should automatically build `net8.0-windows`.
    *   Run `set SISRUA_BUILD_NET48_ACAD2021=1 && build_release.cmd` to build `net48` for 2021.
    *   Run `set SISRUA_BUILD_NET48_ACAD2024=1 && build_release.cmd` to build `net48` for 2024.
2.  Run `organizar_projeto.cmd` to create the `sisRUA.bundle` which should now include all three DLL variants.
3.  Deploy the generated `sisRUA.bundle` to the AutoCAD Plugins folder (e.g., `%APPDATA%\Autodesk\ApplicationPlugins`).

---

### Test Case 1: Plugin Loading and Initialization (AutoCAD 2021)
*   **Description:** Verify the plugin loads successfully in AutoCAD 2021 and the backend starts without errors.
*   **Steps:**
    1.  Start AutoCAD 2021.
    2.  Open a new drawing.
    3.  Type `SISRUA` in the command line and press Enter.
*   **Expected Results:**
    *   No error messages or crashes on AutoCAD startup.
    *   The `sisRUA` palette window appears.
    *   The AutoCAD command line displays messages indicating backend initialization.
    *   Check `%LOCALAPPDATA%\sisRUA\logs\` for `sisRUA_plugin_[timestamp].log`. The log should contain "sisRUA Plugin: Initialize() called." and no critical errors.
    *   The backend process (`sisrua_backend.exe` or `python.exe`) should be running in Task Manager.

### Test Case 2: Core Functionality - Generate OSM (AutoCAD 2021)
*   **Description:** Verify that generating OSM data works correctly.
*   **Steps:**
    1.  Perform Test Case 1 steps.
    2.  In the `sisRUA` palette, enter valid latitude, longitude, and radius (e.g., a known area with roads).
    3.  Click the "Gerar OSM" (Generate OSM) button.
    4.  Observe the AutoCAD command line and the drawing area.
*   **Expected Results:**
    *   Progress messages are displayed in the AutoCAD command line and/or the palette.
    *   Polylines representing OSM roads are drawn in the active drawing.
    *   The "SISRUA_ATTRIB" MText is added to the drawing.
    *   No error messages or crashes.
    *   The plugin log file should contain "GerarProjetoOsm called" and related INFO messages, with no errors.

### Test Case 3: Core Functionality - Import GeoJSON (AutoCAD 2021)
*   **Description:** Verify that importing GeoJSON data works correctly via drag-and-drop.
*   **Steps:**
    1.  Perform Test Case 1 steps.
    2.  Prepare a valid GeoJSON file (e.g., a simple polygon or line feature).
    3.  Drag and drop the GeoJSON file onto the `sisRUA` palette.
    4.  Observe the AutoCAD command line and the drawing area.
*   **Expected Results:**
    *   Messages indicating GeoJSON import are displayed.
    *   The GeoJSON features are drawn as polylines in the active drawing.
    *   No error messages or crashes.
    *   The plugin log file should contain "ImportarDadosCampo called" and related INFO messages, with no errors.

### Test Case 4: Setting Scale (AutoCAD 2021)
*   **Description:** Verify the `SISRUAESCALA` command functions.
*   **Steps:**
    1.  Perform Test Case 1 steps.
    2.  Type `SISRUAESCALA` in the command line and press Enter.
    3.  Enter a new scale factor (e.g., `1000` for mm).
*   **Expected Results:**
    *   The command prompts for input.
    *   "OK: escala salva." message appears.
    *   No error messages.
    *   Subsequent drawing operations (Test Case 2 or 3) should reflect the new scale.

### Test Case 5: Plugin Shutdown (AutoCAD 2021)
*   **Description:** Verify the plugin shuts down cleanly.
*   **Steps:**
    1.  Perform Test Case 1 steps (ensure backend is running).
    2.  Close AutoCAD 2021.
*   **Expected Results:**
    *   AutoCAD closes without errors.
    *   The backend process (`sisrua_backend.exe` or `python.exe`) is terminated.
    *   The plugin log file should contain "sisRUA Plugin: Terminate() called." and "Backend do sisRUA finalizado." messages.

---

### Test Case 6: Plugin Loading and Initialization (AutoCAD 2024)
*   **Description:** Verify existing functionality for AutoCAD 2024 is maintained.
*   **Steps:**
    1.  Start AutoCAD 2024.
    2.  Open a new drawing.
    3.  Type `SISRUA` in the command line and press Enter.
*   **Expected Results:**
    *   Same as Test Case 1. The `sisRUA` palette should appear, backend initializes, and logs are generated. The `sisRUA_NET48_ACAD2024.dll` should be loaded.

### Test Case 7: Core Functionality - Generate OSM (AutoCAD 2024)
*   **Description:** Verify that generating OSM data works correctly.
*   **Steps:**
    1.  Perform Test Case 6 steps.
    2.  Repeat Test Case 2 steps.
*   **Expected Results:**
    *   Same as Test Case 2.

### Test Case 8: Plugin Loading and Initialization (AutoCAD 2026)
*   **Description:** Verify existing functionality for AutoCAD 2026 is maintained.
*   **Steps:**
    1.  Start AutoCAD 2026.
    2.  Open a new drawing.
    3.  Type `SISRUA` in the command line and press Enter.
*   **Expected Results:**
    *   Same as Test Case 1. The `sisRUA_NET8.dll` should be loaded.

### Test Case 9: Core Functionality - Generate OSM (AutoCAD 2026)
*   **Description:** Verify that generating OSM data works correctly.
*   **Steps:**
    1.  Perform Test Case 8 steps.
    2.  Repeat Test Case 2 steps.
*   **Expected Results:**
    *   Same as Test Case 2.

## Reporting
For each test case, record:
*   AutoCAD Version:
*   Test Result: PASS/FAIL
*   Actual Results:
*   Discrepancies (if any):
*   Relevant log entries (`%LOCALAPPDATA%\sisRUA\logs\sisRUA_plugin_[timestamp].log`):
*   Screenshots (if applicable):

## Debugging Strategy (if failures occur)
1.  Examine the `sisRUA_plugin_[timestamp].log` for exceptions or warnings.
2.  Use the AutoCAD command line output for immediate feedback.
3.  Attach a debugger (Visual Studio) to the AutoCAD process, if possible, to step through the C# code.
4.  Verify that the correct DLL version (`sisRUA_NET48_ACAD2021.dll`, `sisRUA_NET48_ACAD2024.dll`, `sisRUA_NET8.dll`) is indeed being loaded by AutoCAD using tools like Process Explorer or AutoCAD's `NETLOAD` command (`(command "NETLOAD")` and then navigate to the bundle to check which module is shown).
5.  If backend issues, check backend logs (if any are generated) and ensure the Python process starts correctly.
