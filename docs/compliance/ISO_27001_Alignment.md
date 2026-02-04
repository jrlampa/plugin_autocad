# ISO 27001 Alignment Statement (sisRUA)

## 1. Information Security Management System (ISMS)

sisRUA is designed following the security-by-design principles of ISO/IEC 27001.

## 2. Key Controls Implemented

- **Access Control (A.9)**: Implemented via secure token-based authentication (IPC/Webview2).
- **Cryptography (A.10)**: Use of Geometric Hashing for data integrity verification and secure local storage (SQLite/ECC).
- **Operations Security (A.12)**: Automated CI/CD pipelines with vulnerability scanning and hermetic build environments.
- **Physical and Environmental Security (A.11)**: Offline-first architecture ensures data residency within the user's controlled CAD environment.

## 3. Data Integrity

The "Audit Grade" integrity signatures ensure that urban data remains tamper-evident throughout its lifecycle.
