using System;
using System.Diagnostics;
using System.Linq;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Threading;

namespace sisRUA.Core
{
    /// <summary>
    /// Manages port allocation and port-related process operations for the backend.
    /// </summary>
    public class PortManager
    {
        private readonly Action<string> _logger;

        public PortManager(Action<string> logger = null)
        {
            _logger = logger ?? (_ => { });
        }

        /// <summary>
        /// Allocates a port for the backend, preferring the default port.
        /// If the default port is in use and cannot be freed, finds an alternative.
        /// </summary>
        /// <returns>Available port number</returns>
        public int AllocatePort()
        {
            int port = BackendConfiguration.DefaultBackendPort;

            // Try default port first
            if (!IsPortInUse(port))
            {
                _logger($"[PortManager] Using default port {port}");
                return port;
            }

            _logger($"[PortManager] Port {port} is in use. Attempting to free it...");

            // Try to kill the process using the port
            if (TryKillProcessByPort(port))
            {
                Thread.Sleep(BackendConfiguration.PortKillDelayMs);
                
                if (!IsPortInUse(port))
                {
                    _logger($"[PortManager] Successfully freed port {port}");
                    return port;
                }
            }

            // Fall back to dynamic port allocation
            _logger($"[PortManager] Could not free port {port}. Searching for alternative...");
            
            // Try ports in range first
            for (int testPort = BackendConfiguration.DefaultBackendPort + 1; 
                 testPort <= BackendConfiguration.PortSearchRangeMax; 
                 testPort++)
            {
                if (!IsPortInUse(testPort))
                {
                    _logger($"[PortManager] Found available port {testPort} (fallback from default {BackendConfiguration.DefaultBackendPort})");
                    return testPort;
                }
            }

            // Last resort: let OS choose
            int randomPort = ChooseRandomFreePort();
            _logger($"[PortManager] Using OS-assigned port {randomPort} (all predefined ports in use)");
            return randomPort;
        }

        /// <summary>
        /// Checks if a port is currently in use.
        /// </summary>
        public bool IsPortInUse(int port)
        {
            try
            {
                var ipGlobalProperties = IPGlobalProperties.GetIPGlobalProperties();
                var tcpListeners = ipGlobalProperties.GetActiveTcpListeners();
                
                return tcpListeners.Any(endpoint => endpoint.Port == port);
            }
            catch (Exception ex)
            {
                _logger($"[PortManager] Error checking port {port}: {ex.Message}");
                // Conservative: assume port is in use if we can't check
                return true;
            }
        }

        /// <summary>
        /// Attempts to kill the process occupying the specified port.
        /// </summary>
        /// <returns>True if kill command was executed (not necessarily successful)</returns>
        public bool TryKillProcessByPort(int port)
        {
            try
            {
                int? pid = GetProcessIdByPort(port);
                if (pid.HasValue)
                {
                    _logger($"[PortManager] Found process PID {pid.Value} using port {port}. Terminating...");
                    
                    var psi = new ProcessStartInfo("taskkill", $"/F /T /PID {pid.Value}")
                    {
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        WindowStyle = ProcessWindowStyle.Hidden
                    };
                    
                    var proc = Process.Start(psi);
                    proc?.WaitForExit(5000);
                    
                    return proc?.ExitCode == 0;
                }
                else
                {
                    _logger($"[PortManager] No process found using port {port}");
                    return false;
                }
            }
            catch (Exception ex)
            {
                _logger($"[PortManager] Error killing process on port {port}: {ex.Message}");
                return false;
            }
        }

        /// <summary>
        /// Gets the process ID of the process using the specified port.
        /// </summary>
        private int? GetProcessIdByPort(int port)
        {
            try
            {
                var psi = new ProcessStartInfo("netstat", "-ano")
                {
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };

                using (var proc = Process.Start(psi))
                {
                    if (proc == null) return null;

                    string output = proc.StandardOutput.ReadToEnd();
                    proc.WaitForExit();

                    foreach (string line in output.Split('\n'))
                    {
                        if (line.Contains($":{port} ") && line.Contains("LISTENING"))
                        {
                            string[] parts = line.Split(new[] { ' ' }, StringSplitOptions.RemoveEmptyEntries);
                            if (parts.Length >= 5 && int.TryParse(parts[4], out int pid))
                            {
                                return pid;
                            }
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                _logger($"[PortManager] Error getting PID for port {port}: {ex.Message}");
            }

            return null;
        }

        /// <summary>
        /// Chooses a random free port by letting the OS allocate one.
        /// </summary>
        private int ChooseRandomFreePort()
        {
            try
            {
                var listener = new TcpListener(IPAddress.Loopback, 0);
                listener.Start();
                int port = ((IPEndPoint)listener.LocalEndpoint).Port;
                listener.Stop();
                return port;
            }
            catch
            {
                // Fallback to a high random port if OS allocation fails
                return new Random().Next(49152, 65535);
            }
        }
    }
}
