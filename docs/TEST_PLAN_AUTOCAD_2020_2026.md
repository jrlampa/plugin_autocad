# Comprehensive Test Plan - AutoCAD 2020-2026 Compatibility

## Executive Summary

This document provides a comprehensive test plan for verifying sisRUA plugin compatibility across AutoCAD versions 2020 through 2026. It includes both automated and manual test procedures, version-specific considerations, and execution templates.

## Version Support Matrix

| AutoCAD Version | R-Series | .NET Framework | AutoCAD.NET | Support Status | Build Target |
|-----------------|----------|----------------|-------------|----------------|--------------|
| **2020** | R23.1 | 4.7+ | 23.0.0 | ❌ Not Supported* | N/A |
| **2021** | R24.0 | 4.8 | 24.0.0 | ✅ Supported | net48 |
| **2022** | R24.1 | 4.8 | 24.1.0 | ✅ Supported | net48 |
| **2023** | R24.2 | 4.8 | 24.2.0 | ✅ Supported | net48 |
| **2024** | R24.3 | 4.8 | 24.3.0 | ✅ Supported | net48 |
| **2025** | R25.0 | .NET 8 | 25.0.0 | ✅ Supported | net8.0-windows |
| **2026** | R25.1 | .NET 8 | 25.1.0 | ✅ Supported | net8.0-windows |

\* **Note on AutoCAD 2020**: Not supported in current build. Would require separate .NET Framework 4.7 build with AutoCAD.NET 23.0.0 package. This is intentionally excluded to minimize build complexity.

## Test Objectives

1. **Verify compatibility** across all supported AutoCAD versions (2021-2026)
2. **Confirm version detection** and appropriate DLL loading
3. **Validate core functionality** (OSM generation, GeoJSON import, scaling)
4. **Ensure proper initialization and shutdown** across all versions
5. **Document any version-specific issues** or limitations

## Test Scope

### In Scope
- ✅ Plugin loading and initialization
- ✅ Backend process lifecycle (start/stop)
- ✅ Core commands: SISRUA, SISRUAESCALA
- ✅ OSM data generation
- ✅ GeoJSON import (drag-and-drop)
- ✅ Scale configuration
- ✅ Logging functionality
- ✅ WebView2 integration
- ✅ AutoCAD 2021-2026 versions

### Out of Scope
- ❌ AutoCAD 2020 (not supported)
- ❌ AutoCAD versions older than 2020
- ❌ Mac/Linux platforms (Windows only)
- ❌ Network-dependent features (offline-first design)
- ❌ Performance benchmarking (separate test suite)

## Test Environment Requirements

### Hardware
- **CPU**: Intel i5 or equivalent (minimum)
- **RAM**: 8GB minimum, 16GB recommended
- **Disk**: 50GB free space for AutoCAD installations
- **Display**: 1920x1080 minimum resolution

### Software
- **Operating Systems**: Windows 10 (64-bit) or Windows 11
- **AutoCAD Versions**: Clean installations of:
  - AutoCAD 2021 (for R24.0 baseline)
  - AutoCAD 2024 (for R24.3 validation)
  - AutoCAD 2025 or 2026 (for R25.x validation)
- **Additional Requirements**:
  - WebView2 Runtime (latest stable)
  - Python 3.11+ (for fallback/debug scenarios)
  - .NET Framework 4.8
  - .NET 8 Runtime

### Test Data
- Valid GeoJSON files (provided in `/qa/test-data/`)
- Known OSM coordinates with reliable road data
- Sample AutoCAD drawings (.dwg files)

## Pre-Test Setup

### 1. Build Preparation

Execute the following build sequence to generate all necessary artifacts:

```batch
REM Clean previous builds
limpar_projeto.cmd

REM Build all versions
build_release.cmd
```

This generates:
- `release/sisRUA.bundle/Contents/net48/sisRUA.dll` (for AutoCAD 2021-2024)
- `release/sisRUA.bundle/Contents/net8.0-windows/sisRUA.dll` (for AutoCAD 2025-2026)
- `release/sisRUA.bundle/PackageContents.xml` (version mapping)

### 2. Installation

Deploy the bundle to AutoCAD's plugin directory:

```
%APPDATA%\Autodesk\ApplicationPlugins\sisRUA.bundle
```

### 3. Verify Prerequisites

Before testing, confirm:
- [ ] All required AutoCAD versions are installed
- [ ] WebView2 Runtime is installed
- [ ] Bundle is copied to correct location
- [ ] Log directory exists: `%LOCALAPPDATA%\sisRUA\logs`
- [ ] No conflicting versions of sisRUA are installed

## Test Cases

### Test Suite 1: Version Detection and Loading

#### TC-1.1: AutoCAD 2021 - Plugin Loading
**Objective**: Verify plugin loads correctly in AutoCAD 2021  
**Prerequisites**: AutoCAD 2021 installed, sisRUA.bundle deployed  
**AutoCAD Version**: 2021 (R24.0)  
**Expected DLL**: `sisRUA_NET48_ACAD2021.dll` or `net48/sisRUA.dll`

**Steps**:
1. Launch AutoCAD 2021
2. Create a new drawing
3. Observe AutoCAD command line for plugin loading messages
4. Type `SISRUA` and press Enter

**Expected Results**:
- ✅ No error messages during AutoCAD startup
- ✅ sisRUA palette window appears
- ✅ Log file created in `%LOCALAPPDATA%\sisRUA\logs\`
- ✅ Log contains: "sisRUA Plugin: Initialize() called."
- ✅ Backend process visible in Task Manager

**Pass Criteria**: All expected results met  
**Fail Criteria**: Any error message, crash, or missing log entry

---

#### TC-1.2: AutoCAD 2022 - Plugin Loading
**Objective**: Verify plugin loads correctly in AutoCAD 2022  
**AutoCAD Version**: 2022 (R24.1)  
**Expected DLL**: `net48/sisRUA.dll`

**Steps**: Same as TC-1.1  
**Expected Results**: Same as TC-1.1  

---

#### TC-1.3: AutoCAD 2023 - Plugin Loading
**Objective**: Verify plugin loads correctly in AutoCAD 2023  
**AutoCAD Version**: 2023 (R24.2)  
**Expected DLL**: `net48/sisRUA.dll`

**Steps**: Same as TC-1.1  
**Expected Results**: Same as TC-1.1  

---

#### TC-1.4: AutoCAD 2024 - Plugin Loading
**Objective**: Verify plugin loads correctly in AutoCAD 2024  
**AutoCAD Version**: 2024 (R24.3)  
**Expected DLL**: `sisRUA_NET48_ACAD2024.dll` or `net48/sisRUA.dll`

**Steps**: Same as TC-1.1  
**Expected Results**: Same as TC-1.1  

---

#### TC-1.5: AutoCAD 2025 - Plugin Loading (.NET 8)
**Objective**: Verify plugin loads correctly in AutoCAD 2025 with .NET 8  
**AutoCAD Version**: 2025 (R25.0)  
**Expected DLL**: `sisRUA_NET8.dll` or `net8.0-windows/sisRUA.dll`

**Steps**: Same as TC-1.1  
**Expected Results**: Same as TC-1.1, but using .NET 8 runtime  

---

#### TC-1.6: AutoCAD 2026 - Plugin Loading (.NET 8)
**Objective**: Verify plugin loads correctly in AutoCAD 2026 with .NET 8  
**AutoCAD Version**: 2026 (R25.1)  
**Expected DLL**: `net8.0-windows/sisRUA.dll`

**Steps**: Same as TC-1.1  
**Expected Results**: Same as TC-1.1, but using .NET 8 runtime  

---

#### TC-1.7: AutoCAD 2020 - Negative Test (Not Supported)
**Objective**: Verify AutoCAD 2020 correctly rejects the plugin  
**AutoCAD Version**: 2020 (R23.1)  
**Expected Behavior**: Plugin should NOT load

**Steps**:
1. Launch AutoCAD 2020
2. Observe command line for plugin loading attempts

**Expected Results**:
- ✅ Plugin does NOT appear in loaded applications
- ✅ No sisRUA palette appears
- ✅ AutoCAD shows message indicating incompatible plugin or missing dependencies

**Pass Criteria**: Plugin correctly fails to load (expected behavior)  
**Fail Criteria**: Plugin loads unexpectedly in AutoCAD 2020

---

### Test Suite 2: Core Functionality - OSM Generation

#### TC-2.1: OSM Generation - AutoCAD 2021
**Objective**: Verify OSM data generation works in AutoCAD 2021  
**AutoCAD Version**: 2021 (R24.0)

**Steps**:
1. Complete TC-1.1 (ensure plugin is loaded)
2. In sisRUA palette, enter coordinates:
   - Latitude: `-23.550520` (São Paulo example)
   - Longitude: `-46.633308`
   - Radius: `500` meters
3. Click "Gerar OSM" button
4. Wait for processing
5. Observe AutoCAD drawing area

**Expected Results**:
- ✅ Progress indicators shown in palette
- ✅ Polylines drawn representing roads
- ✅ Correct layer assignment (`SISRUA_*` layers)
- ✅ Attribution text added to drawing
- ✅ No error messages in command line
- ✅ Log contains: "GerarProjetoOsm called"

**Pass Criteria**: Roads appear correctly georeferenced  
**Fail Criteria**: No geometry drawn, errors logged, or crash

---

#### TC-2.2 through TC-2.6: OSM Generation - Other Versions
**Objective**: Verify OSM generation across all supported versions  
**Versions**: 2022, 2023, 2024, 2025, 2026

**Steps**: Same as TC-2.1  
**Expected Results**: Same as TC-2.1  

---

### Test Suite 3: Core Functionality - GeoJSON Import

#### TC-3.1: GeoJSON Import - AutoCAD 2021
**Objective**: Verify GeoJSON import via drag-and-drop  
**AutoCAD Version**: 2021 (R24.0)

**Steps**:
1. Complete TC-1.1 (ensure plugin is loaded)
2. Prepare a valid GeoJSON file (e.g., `test-polygon.geojson`)
3. Drag and drop the file onto the sisRUA palette
4. Observe drawing area

**Expected Results**:
- ✅ Import confirmation message
- ✅ GeoJSON features rendered as CAD entities
- ✅ Correct layer assignment
- ✅ Geometry matches GeoJSON coordinates
- ✅ Log contains: "ImportarDadosCampo called"

**Pass Criteria**: GeoJSON imported and rendered correctly  
**Fail Criteria**: Import fails, incorrect geometry, or crash

---

#### TC-3.2 through TC-3.6: GeoJSON Import - Other Versions
**Versions**: 2022, 2023, 2024, 2025, 2026

**Steps**: Same as TC-3.1  
**Expected Results**: Same as TC-3.1  

---

### Test Suite 4: Configuration Commands

#### TC-4.1: Scale Configuration - SISRUAESCALA
**Objective**: Verify scale configuration command works across versions  
**AutoCAD Versions**: 2021, 2022, 2023, 2024, 2025, 2026

**Steps**:
1. Ensure plugin is loaded
2. Type `SISRUAESCALA` in command line
3. Enter scale value: `1000`
4. Press Enter

**Expected Results**:
- ✅ Command prompts for input
- ✅ Confirmation message: "OK: escala salva."
- ✅ No errors
- ✅ Subsequent drawing operations use new scale

---

### Test Suite 5: Plugin Lifecycle

#### TC-5.1: Clean Shutdown - All Versions
**Objective**: Verify plugin shuts down cleanly  
**AutoCAD Versions**: 2021, 2022, 2023, 2024, 2025, 2026

**Steps**:
1. Ensure plugin is loaded and backend is running
2. Close AutoCAD

**Expected Results**:
- ✅ AutoCAD closes without errors
- ✅ Backend process terminates (verify in Task Manager)
- ✅ Log contains: "sisRUA Plugin: Terminate() called."
- ✅ Log contains: "Backend do sisRUA finalizado."

---

## Test Execution Record Template

Use this template for each test case execution:

```markdown
### Test Execution: [Test Case ID]

**Date**: YYYY-MM-DD  
**Tester**: [Name]  
**AutoCAD Version**: [2021/2022/2023/2024/2025/2026]  
**Build Version**: [From VERSION.txt]  
**Test Result**: [ PASS | FAIL | BLOCKED ]

**Actual Results**:
[Describe what actually happened]

**Discrepancies**:
[List any differences from expected results]

**Log Entries** (from `%LOCALAPPDATA%\sisRUA\logs\sisRUA_plugin_[timestamp].log`):
```
[Paste relevant log lines]
```

**Screenshots**:
[Attach or reference screenshots if applicable]

**Additional Notes**:
[Any observations, workarounds, or context]
```

## Version-Specific Considerations

### AutoCAD 2021-2024 (.NET Framework 4.8)
- Uses R24.x API
- May require .NET Framework 4.8 runtime installation
- WebView2 integration tested on older AutoCAD versions

### AutoCAD 2025-2026 (.NET 8)
- Uses R25.x API
- Requires .NET 8 runtime
- Native .NET 8 performance benefits
- Potential breaking changes in AutoCAD .NET API

### AutoCAD 2020 (Not Supported)
- R23.1 API not compatible with current build
- Would require separate build configuration
- Users should upgrade to AutoCAD 2021 or newer

## Debugging Procedures

### If Test Fails

1. **Check Logs**:
   ```
   %LOCALAPPDATA%\sisRUA\logs\sisRUA_plugin_[timestamp].log
   ```

2. **Verify DLL Loading**:
   - Use Process Explorer to check loaded modules
   - Confirm correct DLL version (net48 vs. net8.0-windows)

3. **Check Backend**:
   - Verify `sisrua_backend.exe` or `python.exe` is running
   - Check backend logs if available

4. **Environment Validation**:
   - Confirm WebView2 Runtime is installed
   - Check AutoCAD version matches expectations
   - Verify no conflicting plugins

5. **Debugger Attachment** (Advanced):
   - Attach Visual Studio debugger to AutoCAD process
   - Set breakpoints in Initialize() or command handlers

## Acceptance Criteria

Tests are considered **PASSED** when:
- ✅ All TC-1.x (loading) tests pass for supported versions (2021-2026)
- ✅ TC-1.7 (AutoCAD 2020 negative test) correctly prevents loading
- ✅ At least one OSM generation test passes per version
- ✅ At least one GeoJSON import test passes per version
- ✅ Configuration commands work on all supported versions
- ✅ Clean shutdown verified on all supported versions
- ✅ No critical errors in logs
- ✅ All automated tests (NUnit) pass

Tests are considered **FAILED** when:
- ❌ Plugin crashes on any supported version
- ❌ Core functionality (OSM/GeoJSON) fails on any supported version
- ❌ Backend fails to start on any supported version
- ❌ AutoCAD 2020 unexpectedly loads the plugin
- ❌ Critical errors in logs on any supported version

## Reporting

### Summary Report Format

After completing all tests, generate a summary using this format:

```markdown
# sisRUA AutoCAD 2020-2026 Compatibility Test Summary

**Test Date**: [Date Range]  
**Tester(s)**: [Names]  
**Build Version**: [Version]

## Results Overview

| Version | Load | OSM Gen | GeoJSON | Config | Shutdown | Overall |
|---------|------|---------|---------|--------|----------|---------|
| 2020    | N/A  | N/A     | N/A     | N/A    | N/A      | ❌ Not Supported |
| 2021    | ✅   | ✅      | ✅      | ✅     | ✅       | ✅ PASS |
| 2022    | ✅   | ✅      | ✅      | ✅     | ✅       | ✅ PASS |
| 2023    | ✅   | ✅      | ✅      | ✅     | ✅       | ✅ PASS |
| 2024    | ✅   | ✅      | ✅      | ✅     | ✅       | ✅ PASS |
| 2025    | ✅   | ✅      | ✅      | ✅     | ✅       | ✅ PASS |
| 2026    | ✅   | ✅      | ✅      | ✅     | ✅       | ✅ PASS |

## Critical Issues
[List any critical issues discovered]

## Recommendations
[List any recommendations for improvements]
```

## Traceability

This test plan addresses the requirement:
- **REQ-ID**: COMPAT-001 - Plugin shall support AutoCAD 2021-2026
- **REQ-ID**: COMPAT-002 - Plugin shall correctly handle version detection
- **REQ-ID**: COMPAT-003 - Plugin shall not load on unsupported versions (e.g., 2020)

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-17 | GitHub Copilot | Initial comprehensive test plan for AutoCAD 2020-2026 |

## References

- Original test plan: `docs/TEST_PLAN_V0.1.1_AUTOCAD_COMPAT.md`
- QA strategy: `/qa/test-plan.md`
- Manual test guide: `docs/TESTES_MANUAIS_AUTOCAD.md`
- Autodesk AutoCAD .NET Developer's Guide
- sisRUA Architecture Documentation: `docs/ARQUITETURA.md`
