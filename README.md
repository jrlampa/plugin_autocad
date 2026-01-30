# sisRUA (Sistema de Ruas e Urbanismo para AutoCAD)

**sisRUA** is an advanced AutoCAD plugin designed to bridge the gap between GIS and CAD workflows for urban street design. It enables offline-first georeferenced drawing, OpenStreetMap (OSM) data import, and intelligent feature management directly within AutoCAD.

## Features

- **Offline-First Architecture**: Designed to work without continuous internet connection.
- **GIS Integration**: Seamless import of OSM data (streets, buildings) into AutoCAD with correct georeferencing (UTM/SIRGAS 2000).
- **Modern UI**: Embedded React-based palette for intuitive interaction.
- **Geospatial Backend**: Powerful Python backend using `osmnx`, `geopandas`, and `rasterio`.
- **Docker Support**: Fully containerized backend and frontend for easy deployment and development.

## Prerequisites

- **AutoCAD**: 2021 or newer (Windows).
- **Docker Desktop** (Recommended for backend/frontend).
- **Manual Setup**:
  - Python 3.10+
  - Node.js 20+
  - .NET Framework 4.8 or .NET 8.0 SDK

## Installation & Usage

### Option 1: Docker (Recommended for Backend/Frontend)

You can run the backend API and frontend UI in containers:

```bash
docker-compose up --build
```

- **Frontend**: <http://localhost:8080>
- **Backend**: <http://localhost:8000/docs>

### Option 2: Manual Development Setup

#### Backend (Python)

```bash
cd src/backend
pip install -r requirements.txt
python -m backend.standalone --port 8000
```

#### Frontend (React)

```bash
cd src/frontend
npm install
npm run dev
```

#### AutoCAD Plugin (C#)

1. Open `src/plugin/sisRUA.sln` in Visual Studio 2022.
2. Restore NuGet packages.
3. Build the solution (Debug or Release).
4. Open AutoCAD.
5. Run command `NETLOAD` and select the built `sisRUA.dll`.
6. Run command `SISRUA_HOME` (or palette command) to open the interface.

## Project Structure

```text
c:\plugin_autocad\
├── docs/                   # Roadmaps, Architecture, and Compliance docs
├── src/
│   ├── backend/            # Python FastAPI application (Geospatial logic)
│   ├── frontend/           # React + Vite application (WebView UI)
│   └── plugin/             # C# AutoCAD .NET Plugin (Orchestrator)
├── installer/              # Inno Setup scripts for distribution
├── docker-compose.yml      # Orchestration for containerized services
└── README.md               # Project documentation
```

## Documentation

For detailed architectural decisions and roadmaps, refer to the `docs/` directory:

- [Official Roadmap](docs/ROADMAP%20OFICIAL%20DE%20DESENVOLVIMENTO.txt)
- [Architecture](docs/ARQUITETURA.md)
- [Installation Guide](docs/INSTALACAO.md)

## License

Proprietary / Internal Use Only.
