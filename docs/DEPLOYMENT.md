# sisRUA Deployment Guide

## Overview

sisRUA is a desktop AutoCAD plugin with embedded backend and frontend components. This guide covers deployment strategies for different environments.

## Architecture

```
┌─────────────────────────────────────────┐
│  AutoCAD Plugin (C# .NET)               │
│  - Runs inside AutoCAD process          │
│  - Manages lifecycle of backend/frontend│
└────────────┬────────────────────────────┘
             │
             ├── Spawns Local Backend Process
             │   └─> Python FastAPI (port 5000-5010)
             │
             └── Embeds Frontend (WebView2)
                 └─> React UI (served from local files)
```

## Deployment Modes

### 1. Development Mode (Local)

**Target**: Developers working on the plugin

**Requirements**:
- Windows 10/11
- AutoCAD 2021+ installed
- Visual Studio 2022 (for C# development)
- Python 3.10+ (for backend development)
- Node.js 20+ (for frontend development)
- .NET Framework 4.8 or .NET 8.0 SDK

**Setup**:

```powershell
# 1. Clone repository
git clone https://github.com/jrlampa/plugin_autocad.git
cd plugin_autocad

# 2. Install backend dependencies
cd src/backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 3. Install frontend dependencies
cd ../frontend
npm install

# 4. Build plugin
cd ../plugin
# Open sisRUA.sln in Visual Studio 2022
# Build solution (Debug or Release)

# 5. Load in AutoCAD
# Start AutoCAD
# Type: NETLOAD
# Select: plugin_autocad\src\plugin\bin\Debug\net48\sisRUA.dll
# Run: SISRUA_HOME
```

**Environment Variables** (`.env`):
```env
SISRUA_ENV=development
SISRUA_AUTH_TOKEN=dev-token-change-in-prod
GROQ_API_KEY=your_groq_key_here  # Optional
OPENTOPOGRAPHY_API_KEY=your_key  # Optional
SENTRY_DSN=https://...           # Optional
```

---

### 2. Plugin Distribution Mode (End Users)

**Target**: AutoCAD users installing the plugin

**Distribution Package** includes:
- `sisRUA.dll` - AutoCAD plugin
- `backend/` - Python backend (PyInstaller EXE or embedded Python)
- `frontend/dist/` - Built React app (static files)
- `installer.exe` - Inno Setup installer (optional)

**Installation**:

```powershell
# Option A: Manual Installation
# 1. Extract sisRUA.bundle to:
#    %LOCALAPPDATA%\Autodesk\ApplicationPlugins\

# Option B: Installer
# 1. Run installer.exe
# 2. Follow wizard prompts
# 3. AutoCAD will auto-load on next start
```

**User Data Locations**:
- Configuration: `%LOCALAPPDATA%\sisRUA\`
- Database: `%LOCALAPPDATA%\sisRUA\projects.db`
- Logs: `%LOCALAPPDATA%\sisRUA\logs\backend.log`
- Cache: `%LOCALAPPDATA%\sisRUA\cache\`

---

### 3. Enterprise/SaaS Mode (Cloud Backend)

**Target**: Organizations deploying centralized backend

**Components**:
- **Plugin** (Desktop): Connects to remote backend API
- **Backend** (Cloud): FastAPI deployed on server/container
- **Database**: PostgreSQL/SQLite (with proper replication)

**Backend Deployment** (Docker):

```yaml
# docker-compose.yml
version: '3.8'
services:
  backend:
    build:
      context: ./src/backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - SISRUA_ENV=production
      - SISRUA_AUTH_TOKEN=${SECRET_TOKEN}
      - DATABASE_URL=postgresql://user:pass@db:5432/sisrua
      - SENTRY_DSN=${SENTRY_DSN}
      - GROQ_API_KEY=${GROQ_API_KEY}
    volumes:
      - sisrua_data:/data
    restart: unless-stopped
    
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: sisrua
      POSTGRES_USER: sisrua
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  sisrua_data:
  postgres_data:
```

**Deploy to Cloud**:

```bash
# Build backend
cd src/backend
docker build -t sisrua-backend:latest .

# Deploy to AWS/Azure/GCP
docker push your-registry/sisrua-backend:latest

# Or use Kubernetes
kubectl apply -f k8s/deployment.yaml
```

---

## Build Process

### Backend (PyInstaller)

```bash
cd src/backend

# Install PyInstaller
pip install pyinstaller

# Create executable
pyinstaller --onefile \
  --add-data "backend:backend" \
  --hidden-import uvicorn \
  --hidden-import fastapi \
  standalone.py -n sisrua_backend

# Output: dist/sisrua_backend.exe
```

### Frontend (Vite)

```bash
cd src/frontend

# Build production assets
npm run build

# Output: dist/ (static files)
# Copy to: bundle-template/sisRUA.bundle/Contents/frontend/
```

### Plugin (Visual Studio)

```powershell
# From Visual Studio
# 1. Set Configuration to "Release"
# 2. Build Solution
# 3. Output: src/plugin/bin/Release/net48/sisRUA.dll

# Or from command line (MSBuild)
msbuild src/plugin/sisRUA.csproj -p:Configuration=Release
```

---

## Environment Configuration

### Production Checklist

- [ ] **Security**:
  - [ ] Strong `SISRUA_AUTH_TOKEN` set via environment (not hardcoded)
  - [ ] HTTPS enabled for all network communication
  - [ ] CORS restricted to known origins
  - [ ] Sensitive files have proper permissions (0o600)
  - [ ] Sentry error monitoring configured

- [ ] **Performance**:
  - [ ] Database indexes created (run migrations)
  - [ ] Cache directory configured with adequate space
  - [ ] Log rotation enabled
  - [ ] Resource limits set (if containerized)

- [ ] **Reliability**:
  - [ ] Health check endpoint responding (`/api/v1/health`)
  - [ ] Graceful shutdown configured
  - [ ] Backup strategy for database
  - [ ] Monitoring alerts configured

- [ ] **Compliance**:
  - [ ] Audit logging enabled
  - [ ] Data retention policies configured
  - [ ] GDPR/privacy requirements met (if applicable)

### Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SISRUA_ENV` | No | `development` | Environment mode (development/production) |
| `SISRUA_AUTH_TOKEN` | Yes (prod) | Generated | Master authentication token |
| `LOCALAPPDATA` | No | OS default | Data/cache directory |
| `GROQ_API_KEY` | No | None | Groq AI API key for AI features |
| `OPENTOPOGRAPHY_API_KEY` | No | None | Elevation data API key |
| `SENTRY_DSN` | No | None | Sentry error tracking DSN |
| `SENTRY_ENVIRONMENT` | No | `development` | Sentry environment tag |
| `WEBHOOK_URL` | No | None | Static webhook listener URL |

---

## Installer Creation (Inno Setup)

```powershell
# Prerequisites: Inno Setup 6.x installed

cd installer

# Edit installer script
# File: sisrua_installer.iss
# - Update version number
# - Update file paths
# - Configure registry entries

# Compile installer
iscc sisrua_installer.iss

# Output: installer/Output/sisRUA_Setup_v1.1.0.exe
```

**Installer Features**:
- Copies plugin bundle to AutoCAD plugins directory
- Registers COM components (if needed)
- Creates start menu shortcuts
- Configures environment variables
- Uninstaller included

---

## Troubleshooting

### Backend Not Starting

```powershell
# Check backend logs
type %LOCALAPPDATA%\sisRUA\logs\backend.log

# Common issues:
# - Port 5000-5010 in use (check with netstat)
# - Missing dependencies (reinstall backend)
# - Permission issues (run as admin once)
```

### Frontend Not Loading

```powershell
# Check WebView2 runtime
# Download from: https://developer.microsoft.com/microsoft-edge/webview2/

# Check frontend files exist
dir bundle-template\sisRUA.bundle\Contents\frontend\dist

# Check backend is responding
curl http://localhost:5000/api/v1/health
```

### Authentication Failures

```powershell
# Reset token file
del %LOCALAPPDATA%\sisRUA\backend_token.txt

# Restart AutoCAD
# Plugin will generate new token
```

---

## Update Strategy

### Minor Updates (Patch)

1. Replace DLL only
2. Restart AutoCAD
3. Backend auto-migrates schema

### Major Updates (Breaking)

1. Backup user data (`%LOCALAPPDATA%\sisRUA\`)
2. Uninstall old version
3. Install new version
4. Run migration tool (if provided)

### Rollback Procedure

1. Restore backup
2. Reinstall previous version
3. Check database compatibility

---

## Performance Optimization

### Database

```sql
-- Run periodic maintenance
VACUUM;
ANALYZE;

-- Check index usage
.schema CadFeatures
```

### Caching

```powershell
# Clear cache if performance degrades
del /S /Q %LOCALAPPDATA%\sisRUA\cache\*
```

### Memory

- Plugin: ~50-100 MB typical
- Backend: ~100-200 MB (depends on GIS operations)
- Frontend: ~30-50 MB

---

## Security Hardening

### File Permissions

```powershell
# Restrict token file to current user only
icacls %LOCALAPPDATA%\sisRUA\backend_token.txt /inheritance:r /grant:r "%USERNAME%:(F)"
```

### Network

```powershell
# Firewall: Allow only localhost connections to backend
New-NetFirewallRule -DisplayName "sisRUA Backend" -Direction Inbound -LocalPort 5000-5010 -Protocol TCP -Action Allow -LocalAddress 127.0.0.1
```

### Audit

```powershell
# Review audit log
type %LOCALAPPDATA%\sisRUA\logs\audit.log
```

---

## Monitoring

### Health Checks

```bash
# Endpoint
GET http://localhost:5000/api/v1/health

# Expected response
{
  "status": "ok",
  "version": "1.1.0",
  "uptime": 3600
}
```

### Metrics

- Request latency (p50, p95, p99)
- Error rate
- Active sessions
- Database query time

### Logging

- Structured logs (JSON format via structlog)
- Sentry integration for errors
- Audit trail for security events

---

## Support

For deployment issues:
1. Check logs in `%LOCALAPPDATA%\sisRUA\logs\`
2. Review [SECURITY.md](../SECURITY.md) for security guidelines
3. Consult [README.md](../README.md) for architecture details
4. Contact: support@sisrua.com

---

## License

Proprietary / Internal Use Only

Last Updated: 2026-02-16
