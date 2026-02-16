using System;
using System.IO;

namespace sisRUA.Core
{
    /// <summary>
    /// Manages persistent state for the backend process (port, PID, token).
    /// </summary>
    public class BackendStateManager
    {
        private readonly string _stateDirectory;
        private readonly Action<string> _logger;

        public BackendStateManager(string stateDirectory, Action<string> logger = null)
        {
            _stateDirectory = stateDirectory ?? throw new ArgumentNullException(nameof(stateDirectory));
            _logger = logger ?? (_ => { });
            
            EnsureStateDirectoryExists();
        }

        /// <summary>
        /// Reads the last persisted backend port.
        /// </summary>
        /// <returns>Port number, or 0 if not found or invalid</returns>
        public int ReadLastPort()
        {
            return ReadInt(BackendConfiguration.PortPersistenceFile);
        }

        /// <summary>
        /// Reads the last persisted backend process ID.
        /// </summary>
        /// <returns>Process ID, or 0 if not found or invalid</returns>
        public int ReadLastPid()
        {
            return ReadInt(BackendConfiguration.PidPersistenceFile);
        }

        /// <summary>
        /// Reads the last persisted backend authentication token.
        /// </summary>
        /// <returns>Token string, or null if not found</returns>
        public string ReadLastToken()
        {
            return ReadString(BackendConfiguration.TokenPersistenceFile);
        }

        /// <summary>
        /// Persists the backend port.
        /// </summary>
        public void PersistPort(int port)
        {
            WriteString(BackendConfiguration.PortPersistenceFile, port.ToString());
            _logger($"[BackendStateManager] Persisted port: {port}");
        }

        /// <summary>
        /// Persists the backend process ID.
        /// </summary>
        public void PersistPid(int pid)
        {
            WriteString(BackendConfiguration.PidPersistenceFile, pid.ToString());
            _logger($"[BackendStateManager] Persisted PID: {pid}");
        }

        /// <summary>
        /// Persists the backend authentication token.
        /// NOTE: Currently stored in plaintext. File permissions restrict access to current user.
        /// Future enhancement: Implement encryption at rest using Windows DPAPI (ProtectedData class).
        /// </summary>
        public void PersistToken(string token)
        {
            if (string.IsNullOrWhiteSpace(token))
            {
                _logger("[BackendStateManager] Warning: Attempted to persist empty token");
                return;
            }

            WriteString(BackendConfiguration.TokenPersistenceFile, token);
            _logger("[BackendStateManager] Persisted authentication token");
        }

        /// <summary>
        /// Clears all persisted backend state.
        /// </summary>
        public void ClearAllState()
        {
            ClearFile(BackendConfiguration.PortPersistenceFile);
            ClearFile(BackendConfiguration.PidPersistenceFile);
            ClearFile(BackendConfiguration.TokenPersistenceFile);
            _logger("[BackendStateManager] Cleared all persisted state");
        }

        /// <summary>
        /// Clears only the PID file (useful after successful cleanup).
        /// </summary>
        public void ClearPid()
        {
            ClearFile(BackendConfiguration.PidPersistenceFile);
        }

        private void EnsureStateDirectoryExists()
        {
            try
            {
                if (!Directory.Exists(_stateDirectory))
                {
                    Directory.CreateDirectory(_stateDirectory);
                    _logger($"[BackendStateManager] Created state directory: {_stateDirectory}");
                }
            }
            catch (Exception ex)
            {
                _logger($"[BackendStateManager] Error creating state directory: {ex.Message}");
            }
        }

        private int ReadInt(string fileName)
        {
            try
            {
                string filePath = Path.Combine(_stateDirectory, fileName);
                if (File.Exists(filePath))
                {
                    string content = File.ReadAllText(filePath).Trim();
                    if (int.TryParse(content, out int value))
                    {
                        return value;
                    }
                }
            }
            catch (Exception ex)
            {
                _logger($"[BackendStateManager] Error reading {fileName}: {ex.Message}");
            }

            return 0;
        }

        private string ReadString(string fileName)
        {
            try
            {
                string filePath = Path.Combine(_stateDirectory, fileName);
                if (File.Exists(filePath))
                {
                    return File.ReadAllText(filePath).Trim();
                }
            }
            catch (Exception ex)
            {
                _logger($"[BackendStateManager] Error reading {fileName}: {ex.Message}");
            }

            return null;
        }

        private void WriteString(string fileName, string content)
        {
            try
            {
                EnsureStateDirectoryExists();
                string filePath = Path.Combine(_stateDirectory, fileName);
                File.WriteAllText(filePath, content);
            }
            catch (Exception ex)
            {
                _logger($"[BackendStateManager] Error writing {fileName}: {ex.Message}");
            }
        }

        private void ClearFile(string fileName)
        {
            try
            {
                string filePath = Path.Combine(_stateDirectory, fileName);
                if (File.Exists(filePath))
                {
                    File.Delete(filePath);
                }
            }
            catch (Exception ex)
            {
                _logger($"[BackendStateManager] Error clearing {fileName}: {ex.Message}");
            }
        }
    }
}
