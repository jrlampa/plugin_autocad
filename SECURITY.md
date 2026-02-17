# Security Policy

## Dependency Management

### Python Dependencies

All Python dependencies are pinned to specific versions in `requirements*.txt` files to ensure reproducible builds and security.

**Security Updates Applied:**
- `requests`: Updated to 2.32.4 (fixes CVE-2024-35195, CVE-2024-47081)
- `urllib3`: Updated to 2.6.3 (fixes multiple CVEs including CVE-2025-66418, CVE-2025-66471, CVE-2026-21441)

**Dependency Audit:**
Run `pip-audit` regularly to check for new vulnerabilities:
```bash
cd src/backend
pip install pip-audit
pip-audit
```

### Node.js Dependencies

Frontend dependencies are managed via `package.json` with npm.

**Security Updates Applied:**
- `axios`: Updated to ^1.13.2 (fixes GHSA-43fc-jf86-j433)

**Known Development-Only Issues:**
- `esbuild` (via vitest): Moderate severity issue affecting development server only. Not exposed in production builds.

**Dependency Audit:**
```bash
cd src/frontend
npm audit
npm audit fix  # Apply automatic fixes
```

### .NET Dependencies

.NET dependencies are managed via NuGet package references in `.csproj` files.

**Audit Process:**
- Use Visual Studio's built-in NuGet vulnerability checker
- Or use `dotnet list package --vulnerable`

## Dependency Update Policy

1. **Critical Security Updates**: Apply immediately when vulnerabilities are disclosed
2. **Regular Updates**: Review and update dependencies quarterly
3. **Testing**: All dependency updates must pass full test suite before merging
4. **Pinning Strategy**: 
   - Python: Pin exact versions (`==`)
   - Node.js: Use caret ranges for non-breaking updates (`^`)
   - .NET: Review updates manually via NuGet

## Reporting Vulnerabilities

If you discover a security vulnerability in this project:

1. **Do NOT** open a public issue
2. Contact the maintainers privately
3. Include detailed information about the vulnerability
4. Allow reasonable time for a fix before public disclosure

## Security Best Practices

### Authentication

- All API endpoints require `X-SisRua-Token` header
- Session tokens expire after 30 minutes of inactivity
- Master bootstrap token stored in environment variable `SISRUA_AUTH_TOKEN`
- IPC tokens exchanged via named pipes (Windows local-only)

### Token Storage

⚠️ **Known Issue**: Backend token persistence in `backend_token.txt` is currently unencrypted. 
- Mitigation: File permissions restricted to current user (0o600)
- Planned: Implement encryption at rest using Windows DPAPI

### HTTPS

- Production deployments **MUST** use HTTPS
- Development mode allows HTTP for localhost only
- CORS configured to restrict origins

### Environment Variables

- Never commit `.env` files (enforced via `.gitignore`)
- Use `.env.example` as template with placeholder values
- Production secrets managed via secure environment configuration

## Security Checklist for Deployments

- [ ] All dependencies up to date and audited
- [ ] HTTPS enabled and enforced
- [ ] Environment variables properly configured
- [ ] Session timeout configured appropriately
- [ ] CORS origins restricted to known domains
- [ ] Log monitoring and alerting enabled (Sentry)
- [ ] File permissions verified on sensitive files
- [ ] Backup authentication tokens stored securely
- [ ] Rate limiting configured (if applicable)

## Audit Log

| Date | Auditor | Changes | Status |
|------|---------|---------|--------|
| 2026-02-16 | GitHub Copilot | Initial security audit, dependency updates | ✅ Complete |
