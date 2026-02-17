# AutoCAD 2020-2026 Compatibility Tests

This directory contains automated test suites for verifying sisRUA plugin compatibility across AutoCAD versions 2020-2026.

## Test Files

### AutoCADVersionCompatibilityTests.cs
**Purpose**: Validates AutoCAD version to R-series mapping and support status

**Test Coverage**:
- Version to R-series mapping (2020-2026)
- .NET Framework requirements per version
- Supported vs. unsupported version detection
- Complete coverage verification for all versions

**Key Tests**:
- `VerifyVersionMapping_CorrectRSeries`: Ensures correct R-series mapping for each AutoCAD version
- `VerifyRuntimeRequirements_SupportedVersions`: Validates .NET Framework/runtime requirements
- `VerifyUnsupportedVersions_AutoCAD2020`: Confirms AutoCAD 2020 is properly marked as unsupported
- `VerifyVersionRanges_R24Series`: Validates R24.x range (2021-2024)
- `VerifyVersionRanges_R25Series`: Validates R25.x range (2025-2026)
- `VerifyCompleteCoverage_2020Through2026`: Ensures all versions are accounted for

**Total Tests**: 13

---

### BuildConfigurationTests.cs
**Purpose**: Validates build configuration, PackageContents.xml, and runtime requirements

**Test Coverage**:
- PackageContents.xml existence and structure
- R24.x and R25.x RuntimeRequirements entries
- Absence of R23.x support (AutoCAD 2020)
- AutoCAD and Civil3D platform entries
- Module paths for net48 and net8.0-windows
- Required command definitions (SISRUA, SISRUAESCALA)
- Version range continuity

**Key Tests**:
- `VerifyPackageContentsXml_Exists`: Confirms PackageContents.xml exists
- `VerifyPackageContentsXml_HasR24RuntimeRequirements`: Validates R24.0-R24.3 entries
- `VerifyPackageContentsXml_HasR25RuntimeRequirements`: Validates R25.0-R25.1 entries
- `VerifyPackageContentsXml_NoR23Support`: Ensures R23.x is not present
- `VerifyPackageContentsXml_HasCorrectModulePaths`: Validates DLL paths
- `VerifyPackageContentsXml_HasRequiredCommands`: Confirms command definitions
- `VerifyVersionRanges_NoGaps`: Ensures continuous version support

**Total Tests**: 9

---

## Version Support Summary

| AutoCAD Version | R-Series | .NET Framework | Support Status | Build Target |
|-----------------|----------|----------------|----------------|--------------|
| **2020** | R23.1 | .NET 4.7+ | ❌ Not Supported | N/A |
| **2021** | R24.0 | .NET 4.8 | ✅ Supported | net48 |
| **2022** | R24.1 | .NET 4.8 | ✅ Supported | net48 |
| **2023** | R24.2 | .NET 4.8 | ✅ Supported | net48 |
| **2024** | R24.3 | .NET 4.8 | ✅ Supported | net48 |
| **2025** | R25.0 | .NET 8 | ✅ Supported | net8.0-windows |
| **2026** | R25.1 | .NET 8 | ✅ Supported | net8.0-windows |

## Running Tests

### Prerequisites
- Windows 10/11 (64-bit)
- Visual Studio 2022 or .NET SDK 8.0+
- NUnit test runner

### Run All Tests
```bash
cd src/plugin/tests
dotnet test
```

### Run Specific Test Suite
```bash
# Version compatibility tests only
dotnet test --filter "FullyQualifiedName~AutoCADVersionCompatibilityTests"

# Build configuration tests only
dotnet test --filter "FullyQualifiedName~BuildConfigurationTests"
```

### Run Specific Test
```bash
dotnet test --filter "Name~VerifyVersionMapping_CorrectRSeries"
```

## Expected Results

When all tests pass:
- ✅ 22 total tests passed (13 version + 9 build config)
- ✅ 0 failures
- ✅ Confirms support for AutoCAD 2021-2026
- ✅ Confirms AutoCAD 2020 is correctly excluded
- ✅ Validates build configuration for all target versions

## Test Philosophy

These tests follow the principle of **explicit documentation through testing**:

1. **Version Mapping**: Hard-coded version-to-R-series mapping serves as documentation
2. **Support Status**: Explicitly defined supported/unsupported versions
3. **Configuration Validation**: XML configuration is validated against expectations
4. **Regression Prevention**: Changes to version support must update tests

## Integration with Manual Tests

These automated tests complement the manual test plan:
- **Automated**: Version detection, configuration validation, build verification
- **Manual**: Actual AutoCAD integration, UI interaction, drawing functionality

See:
- [Comprehensive Manual Test Plan](../../../docs/TEST_PLAN_AUTOCAD_2020_2026.md)
- [Test Execution Record Template](../../../qa/test-execution/execution-record-autocad-2020-2026.md)

## Maintenance

When adding support for new AutoCAD versions:

1. Update `VersionToRSeriesMap` in AutoCADVersionCompatibilityTests.cs
2. Update `SupportedVersions` set
3. Add test cases for the new version
4. Update PackageContents.xml with new R-series range
5. Verify BuildConfigurationTests pass with new configuration
6. Update manual test plan with new version test cases

## References

- [Autodesk AutoCAD .NET Developer's Guide](https://www.autodesk.com/developer-network/platform-technologies/autocad)
- [sisRUA Architecture Documentation](../../../docs/ARQUITETURA.md)
- [Original Compatibility Test Plan](../../../docs/TEST_PLAN_V0.1.1_AUTOCAD_COMPAT.md)
