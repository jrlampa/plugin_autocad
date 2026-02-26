// Core/BackendManager.cs
// Orquestração principal: Start, Stop, Watchdog e health checks.
// Métodos de processo divididos em BackendProcess.cs (partial).
// Helpers de persistência em BackendPersistence.cs (partial).
using System;
using System.Diagnostics;
using System.IO;
using System.Net.Http;
using System.Reflection;
using System.Threading;
using System.Threading.Tasks;

namespace sisRUA.Core
{
    public partial class BackendManager
    {
        private Process _pythonProcess;
        private static readonly HttpClient _healthClient = new HttpClient { Timeout = TimeSpan.FromSeconds(1.5) };
        private static readonly object _backendLock = new object();
        private System.Windows.Forms.Timer _watchdogTimer;
        private int _healthFailCount = 0;

        // Callbacks for logging
        public Action<string> OnLog { get; set; }
        public Action<string> OnAlert { get; set; }

        public int Port { get; private set; }
        public string BaseUrl => Port > 0 ? $"http://127.0.0.1:{Port}" : null;
        public string AuthToken { get; private set; }

        public const string AuthHeaderName = "X-SisRua-Token";
        private const string AuthEnvVarName = "SISRUA_AUTH_TOKEN";

        public void Start()
        {
            Log("BackendManager.Start() called.");

            try
            {
                string pluginPath = Assembly.GetExecutingAssembly().Location;
                string projectRoot = FindProjectRoot(Path.GetDirectoryName(pluginPath));

                if (string.IsNullOrEmpty(projectRoot))
                {
                    Alert("Erro Crítico: Não foi possível localizar a pasta raiz do sisRUA contendo o diretório 'backend'.");
                    return;
                }

                using (var startupMutex = new Mutex(false, @"Global\sisRUA_Backend_Init"))
                {
                    bool hasHandle = false;
                    try { hasHandle = startupMutex.WaitOne(10000, false); } catch (AbandonedMutexException) { hasHandle = true; }

                    try
                    {
                        lock (_backendLock)
                        {
                            InitializeBackendProcess(projectRoot);
                        }
                    }
                    finally
                    {
                        if (hasHandle) startupMutex.ReleaseMutex();
                    }
                }

                StartWatchdog();
            }
            catch (Exception ex)
            {
                Alert("Erro durante BackendManager.Start(): " + ex.Message);
                _pythonProcess = null;
            }
        }

        public void Stop()
        {
            StopWatchdog();
            Log("BackendManager.Stop() called.");

            try
            {
                // 1. Attempt Graceful Shutdown via API
                if (IsBackendHealthy() && IsBackendAuthorized())
                {
                    if (ShutdownBackendGracefully())
                    {
                        Log("Backend finalizado graciosamente via API.");
                        _pythonProcess?.Dispose();
                        _pythonProcess = null;
                        return;
                    }
                }

                // 2. Force Kill if graceful failed or not running
                if (_pythonProcess != null && !_pythonProcess.HasExited)
                {
                    Log("Graceful shutdown falhou ou timeout. Forçando encerramento...");
                    KillProcessTree(_pythonProcess.Id);
                    _pythonProcess.Dispose();
                    _pythonProcess = null;
                    Log("Backend do sisRUA finalizado (Force Kill).");
                    return;
                }

                // Fallback: kill persisted PID
                int pid = TryReadLastBackendPid();
                if (pid > 0)
                {
                    try
                    {
                        KillProcessTree(pid);
                        Log($"Processo órfão (PID {pid}) finalizado via fallback.");
                    }
                    catch (Exception ex) { Log($"Erro ao finalizar processo órfão: {ex.Message}"); }
                }
            }
            catch (Exception ex)
            {
                Log($"[ERROR] Exceção ao tentar finalizar o backend: {ex.Message}");
            }
        }

        private bool ShutdownBackendGracefully()
        {
            try
            {
                Log("Enviando comando de shutdown para API...");
                var request = new HttpRequestMessage(HttpMethod.Post, $"{BaseUrl}/api/v1/management/shutdown");
                request.Headers.Add(AuthHeaderName, AuthToken);

                var response = _healthClient.SendAsync(request).Result;
                if (response.IsSuccessStatusCode)
                {
                    if (_pythonProcess != null)
                        return _pythonProcess.WaitForExit(3000);
                    return true;
                }
                Log($"Falha no shutdown via API: {response.StatusCode}");
                return false;
            }
            catch (Exception ex)
            {
                Log($"Erro ao tentar shutdown gracioso: {ex.Message}");
                return false;
            }
        }

        public bool EnsureHealthy(TimeSpan timeout) => WaitForBackendHealthy(timeout);

        private void InitializeBackendProcess(string projectRoot)
        {
            // 1. Check if already running/healthy
            int previousPort = TryReadLastBackendPort();
            if (previousPort > 0) Port = previousPort;

            string previousToken = TryReadLastBackendToken();
            if (!string.IsNullOrWhiteSpace(previousToken)) AuthToken = previousToken;
            else
            {
                AuthToken = Guid.NewGuid().ToString("N");
                PersistBackendToken(AuthToken);
            }

            if (IsBackendHealthy() && IsBackendAuthorized())
            {
                Log($"Backend já está rodando (health/auth OK) em {BaseUrl}.");
                return;
            }

            // 2. Check previous PID
            int previousPid = TryReadLastBackendPid();
            if (previousPid > 0)
            {
                try
                {
                    Process p = Process.GetProcessById(previousPid);
                    if (p != null && !p.HasExited)
                    {
                        Log($"Backend (PID {previousPid}) detectado. Aguardando...");
                        if (WaitForBackendHealthy(TimeSpan.FromSeconds(15)) && IsBackendAuthorized())
                        {
                            Log($"Backend (PID {previousPid}) reutilizado com sucesso.");
                            _pythonProcess = p;
                            return;
                        }

                        Log($"Backend (PID {previousPid}) não respondeu. Reiniciando...");
                        KillProcessTree(previousPid);
                    }
                }
                catch (ArgumentException) { /* Process gone */ }
                catch (Exception ex) { Log($"[Aviso] Erro ao verificar PID anterior: {ex.Message}"); }
            }

            // 3. Start New
            Port = ChooseFreePort();
            PersistBackendPort(Port);
            AuthToken = Guid.NewGuid().ToString("N");
            PersistBackendToken(AuthToken);

            string backendExePath = Path.Combine(projectRoot, "backend", "sisrua_backend.exe");
            if (File.Exists(backendExePath))
            {
                StartExeBackend(backendExePath, projectRoot);
            }
            else
            {
#if DEBUG
                StartPythonBackend(projectRoot);
#else
                Alert("Erro Crítico: sisrua_backend.exe não encontrado.");
#endif
            }
        }

        // --- Watchdog ---

        private void StartWatchdog()
        {
            if (_watchdogTimer != null) return;
            _watchdogTimer = new System.Windows.Forms.Timer { Interval = 30000 };
            _watchdogTimer.Tick += (s, e) => CheckHealthAsync();
            _watchdogTimer.Start();
            Log("Watchdog ativado.");
        }

        private void StopWatchdog()
        {
            if (_watchdogTimer != null)
            {
                _watchdogTimer.Stop();
                _watchdogTimer.Dispose();
                _watchdogTimer = null;
            }
        }

        private async void CheckHealthAsync()
        {
            if (Monitor.TryEnter(_backendLock))
            {
                try
                {
                    bool isHealthy = await Task.Run(() => IsBackendHealthy());
                    if (!isHealthy)
                    {
                        Interlocked.Increment(ref _healthFailCount);
                        Log($"[Watchdog] Backend não responde ({_healthFailCount}/3).");
                        if (_healthFailCount >= 3)
                        {
                            Log("[Watchdog] Backend crítico. Tentando reinício automático...");
                            _healthFailCount = 0;
                            InitializeBackendProcess(FindProjectRoot(Assembly.GetExecutingAssembly().Location));
                        }
                    }
                    else
                    {
                        _healthFailCount = 0;
                    }
                }
                finally
                {
                    Monitor.Exit(_backendLock);
                }
            }
        }

        // --- Health Checks ---

        private bool IsBackendHealthy()
        {
            if (Port <= 0) return false;
            try
            {
                var response = _healthClient.GetAsync($"{BaseUrl}/api/v1/health").Result;
                return response.IsSuccessStatusCode;
            }
            catch { return false; }
        }

        private bool IsBackendAuthorized()
        {
            if (Port <= 0 || string.IsNullOrEmpty(AuthToken)) return false;
            try
            {
                var request = new HttpRequestMessage(HttpMethod.Get, $"{BaseUrl}/api/v1/auth/check");
                request.Headers.Add(AuthHeaderName, AuthToken);
                var response = _healthClient.SendAsync(request).Result;
                return response.IsSuccessStatusCode;
            }
            catch { return false; }
        }

        private bool WaitForBackendHealthy(TimeSpan timeout)
        {
            var sw = Stopwatch.StartNew();
            while (sw.Elapsed < timeout)
            {
                if (IsBackendHealthy()) return true;
                Thread.Sleep(500);
            }
            return false;
        }

        // --- Logging ---
        private void Log(string msg) => OnLog?.Invoke(msg);
        private void Alert(string msg) => OnAlert?.Invoke(msg);
    }
}
