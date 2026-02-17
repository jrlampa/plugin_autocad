using System;

namespace sisRUA.Core
{
    /// <summary>
    /// Centralized configuration constants for backend process management.
    /// </summary>
    public static class BackendConfiguration
    {
        // Port Configuration
        /// <summary>Default backend port (used as first preference)</summary>
        public const int DefaultBackendPort = 5000;
        
        /// <summary>Maximum port to search when default is unavailable</summary>
        public const int PortSearchRangeMax = 5010;

        // Timeouts
        /// <summary>Maximum time to wait for backend health check during startup (seconds)</summary>
        public const int BackendHealthTimeoutSeconds = 90;
        
        /// <summary>Health check timeout for Python backend (seconds)</summary>
        public const int PythonBackendHealthTimeoutSeconds = 60;
        
        /// <summary>Timeout for waiting for previous PID process (seconds)</summary>
        public const int PreviousPidWaitTimeoutSeconds = 15;
        
        /// <summary>Timeout for Named Pipe server availability (seconds)</summary>
        public const int PipeServerTimeoutSeconds = 45;
        
        /// <summary>Timeout for Named Pipe connection (milliseconds)</summary>
        public const int IpcConnectTimeoutMs = 2000;

        /// <summary>Timeout for individual health check HTTP request (seconds)</summary>
        public const double HealthCheckRequestTimeoutSeconds = 1.5;

        /// <summary>Timeout for WebView navigation failsafe (seconds)</summary>
        public const int WebViewNavigationTimeoutSeconds = 15;

        /// <summary>Timeout for WebView backend health pre-check (seconds)</summary>
        public const int WebViewBackendHealthCheckSeconds = 5;

        // Retry Configuration
        /// <summary>Maximum number of IPC token retrieval attempts</summary>
        public const int IpcMaxRetries = 3;
        
        /// <summary>Base delay for IPC retry exponential backoff (milliseconds)</summary>
        public const int IpcRetryBaseDelayMs = 1000;

        /// <summary>Maximum number of WebView navigation retry attempts</summary>
        public const int WebViewNavigationMaxRetries = 2;
        
        /// <summary>Delay before retrying WebView navigation (milliseconds)</summary>
        public const int WebViewNavigationRetryDelayMs = 2000;

        // Watchdog Configuration
        /// <summary>Interval for backend health watchdog checks (milliseconds)</summary>
        public const int WatchdogIntervalMs = 30000;
        
        /// <summary>Number of consecutive health failures before watchdog restart</summary>
        public const int MaxHealthFailures = 3;

        // Process Management
        /// <summary>Time to wait after killing port-occupying process (milliseconds)</summary>
        public const int PortKillDelayMs = 1000;
        
        /// <summary>Timeout for mutex acquisition during backend initialization (milliseconds)</summary>
        public const int InitMutexTimeoutMs = 15000;

        /// <summary>Time to wait for graceful shutdown before force kill (seconds)</summary>
        public const int GracefulShutdownWaitSeconds = 3;

        // IPC Configuration
        /// <summary>Named pipe name for IPC communication</summary>
        public const string IpcPipeName = "sisrua_backend";
        
        /// <summary>IPC request message for token retrieval</summary>
        public const string IpcGetTokenRequest = "GET_TOKEN";
        
        /// <summary>Buffer size for IPC communication (bytes)</summary>
        public const int IpcBufferSize = 4096;

        /// <summary>Delay between pipe server availability checks (milliseconds)</summary>
        public const int PipeCheckDelayMs = 500;

        /// <summary>Initial pipe connection test timeout (milliseconds)</summary>
        public const int PipeTestConnectionMs = 100;

        // File Names
        /// <summary>File name for persisted backend port</summary>
        public const string PortPersistenceFile = "backend_port.txt";
        
        /// <summary>File name for persisted backend token</summary>
        public const string TokenPersistenceFile = "backend_token.txt";
        
        /// <summary>File name for persisted backend PID</summary>
        public const string PidPersistenceFile = "backend_pid.txt";

        // Backend Paths
        /// <summary>Relative path to backend executable from project root</summary>
        public const string BackendExeRelativePath = "backend\\sisrua_backend.exe";
        
        /// <summary>Relative path to backend directory from project root</summary>
        public const string BackendDirRelativePath = "backend";

        // HTTP Client Configuration
        /// <summary>User agent for backend health check requests</summary>
        public const string HealthCheckUserAgent = "sisRUA-Plugin/1.0";
    }
}
