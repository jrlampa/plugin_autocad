# sisRUA Desktop UI Automation (FlaUI)

This project contains End-to-End (E2E) UI tests for the sisRUA AutoCAD plugin, using [FlaUI](https://github.com/FlaUI/FlaUI).

## Prerequisites

- **OS**: Windows 10/11
- **Software**: AutoCAD 2021+ installed and running.
- **Plugin**: sisRUA plugin must be `NETLOAD`ed in AutoCAD before running tests.

## How to Run

1. Open AutoCAD.
2. Load the plugin (`NETLOAD` -> `sisRUA.dll`).
3. Run command `SISRUA_HOME` to show the palette.
4. Run tests via `dotnet test` or Visual Studio Test Explorer.

```powershell
cd tests/ui_desktop
dotnet test
```

## CI/CD Limitations

Running these tests in GitHub Actions requires a self-hosted runner with AutoCAD installed and an active desktop session. Currently, these tests are designed for **local verification** or dedicated QA VMs.
