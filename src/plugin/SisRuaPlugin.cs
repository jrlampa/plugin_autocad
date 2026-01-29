using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.ApplicationServices.Core;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Net.Http;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;

[assembly: ExtensionApplication(typeof(sisRUA.SisRuaPlugin))]
[assembly: CommandClass(typeof(sisRUA.SisRuaPalette))]

namespace sisRUA
{
    /// <summary>
    /// Gerencia o ciclo de vida do processo de backend Python (servidor FastAPI).
    /// </summary>
    public class SisRuaPlugin : IExtensionApplication
    {
        public static SisRuaPlugin Instance { get; private set; }

        private Process _pythonProcess;
        private static Editor _editor => Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument?.Editor;
        private static readonly HttpClient _healthClient = new HttpClient { Timeout = TimeSpan.FromSeconds(1.5) };
        private static readonly object _backendLock = new object();
        private static TextWriter _logger;

        public static int BackendPort { get; private set; }
        public static string BackendBaseUrl => BackendPort > 0 ? $"http://127.0.0.1:{BackendPort}" : null;

        public const string BackendAuthHeaderName = "X-SisRua-Token";
        private const string BackendAuthEnvVarName = "SISRUA_AUTH_TOKEN";
        public static string BackendAuthToken { get; private set; }

        public static bool EnsureBackendHealthy(TimeSpan timeout)
        {
            return Instance != null && Instance.WaitForBackendHealthy(timeout);
        }

        /// <summary>
        /// Chamado quando o AutoCAD carrega a extensão.
        /// Localiza e inicia o servidor Python de forma robusta.
        /// </summary>
        public void Initialize()
        {
            Instance = this;
            SisRuaLog.OnMessageLogged += (msg) => LogToEditor(msg);

            SetupLogger();
            SisRuaLog.Info("\n>>> sisRUA Plugin: Initialize() called.");

            // Registra um evento para ajudar o AutoCAD a encontrar as DLLs vizinhas
            AppDomain.CurrentDomain.AssemblyResolve += CurrentDomain_AssemblyResolve;

            try
            {
                string pluginPath = Assembly.GetExecutingAssembly().Location;
                string projectRoot = FindProjectRoot(Path.GetDirectoryName(pluginPath));

                if (string.IsNullOrEmpty(projectRoot))
                {
                    LogAndAlert("Erro Crítico: Não foi possível localizar a pasta raiz do sisRUA contendo o diretório 'backend'. O plugin não funcionará.");
                    return;
                }

                // Mutex global para garantir que apenas um processo de inicialização ocorra por vez no SO.
                using (var startupMutex = new Mutex(false, @"Global\sisRUA_Backend_Init"))
                {
                    // Tenta adquirir o mutex por até 10 segundos. Se falhar, assume que outro processo travou e prossegue com cuidado.
                    bool hasHandle = false;
                    try { hasHandle = startupMutex.WaitOne(10000, false); } catch (AbandonedMutexException) { hasHandle = true; }

                    try
                    {
                        lock (_backendLock)
                        {
                            // Se o backend já estiver rodando, não iniciamos um novo processo.
                            int previousPort = TryReadLastBackendPort();
                            if (previousPort > 0) BackendPort = previousPort;

                            string previousToken = TryReadLastBackendToken();
                            if (!string.IsNullOrWhiteSpace(previousToken)) BackendAuthToken = previousToken;

                            // Se não tiver token, gera um.
                            if (string.IsNullOrWhiteSpace(BackendAuthToken))
                            {
                                BackendAuthToken = Guid.NewGuid().ToString("N");
                                PersistBackendToken(BackendAuthToken);
                            }

                            // 1. Verifica se já está saudável e autorizado
                            if (IsBackendHealthy() && IsBackendAuthorized())
                            {
                                LogToEditor($"\n>>> Backend do sisRUA já está rodando (health/auth OK) em {BackendBaseUrl}.");
                                // Tenta readquirir o objeto Process para o Terminate() funcionar depois
                                AttachToExistingProcess();
                                return;
                            }

                            // 2. Se não está saudável, verifica se existe um PID rodando que pode estar "bootando"
                            int previousPid = TryReadLastBackendPid();
                            if (previousPid > 0)
                            {
                                try
                                {
                                    Process p = Process.GetProcessById(previousPid);
                                    if (p != null && !p.HasExited)
                                    {
                                        LogToEditor($"\n>>> Backend (PID {previousPid}) detectado. Aguardando inicialização...");
                                        // Aguarda até 15s para ele ficar saudável
                                        if (WaitForBackendHealthy(TimeSpan.FromSeconds(15)))
                                        {
                                            if (IsBackendAuthorized())
                                            {
                                                LogToEditor($"\n>>> Backend (PID {previousPid}) inicializou com sucesso e foi reutilizado.");
                                                _pythonProcess = p;
                                                return;
                                            }
                                        }
                                        
                                        // Se chegou aqui, ou timeout ou não autorizado. Mata o processo antigo.
                                        LogToEditor($"\n>>> Aviso: Backend (PID {previousPid}) não respondeu corretamente. Reiniciando...");
                                        TryKillProcess(previousPid);
                                    }
                                }
                                catch (ArgumentException) { /* Processo não existe mais */ }
                                catch (System.Exception ex) { LogToEditor($"\n[Aviso] Erro ao verificar PID anterior: {ex.Message}"); }
                            }

                            // 3. Inicia novo processo
                            // Porta dinâmica: escolhe uma porta livre para evitar conflito.
                            BackendPort = ChooseFreePort();
                            PersistBackendPort(BackendPort);

                            // Novo token por sessão
                            BackendAuthToken = Guid.NewGuid().ToString("N");
                            PersistBackendToken(BackendAuthToken);
                        }
                    }
                    finally
                    {
                        if (hasHandle) startupMutex.ReleaseMutex();
                    }
                }

                // Preferência: backend empacotado (EXE) — não depende de Python instalado no usuário.
                // Espera-se que o instalador copie esse arquivo para Contents\backend\sisrua_backend.exe.
                string backendExePath = Path.Combine(projectRoot, "backend", "sisrua_backend.exe");
                if (File.Exists(backendExePath))
                {
                    LogToEditor($"\n>>> Iniciando backend empacotado (sisrua_backend.exe) na porta {BackendPort}...");
                    var exeStart = new ProcessStartInfo(backendExePath)
                    {
                        WorkingDirectory = projectRoot,
                        UseShellExecute = false,
                        CreateNoWindow = true,
                        Arguments = $"--host 127.0.0.1 --port {BackendPort} --log-level warning"
                    };
                    exeStart.EnvironmentVariables[BackendAuthEnvVarName] = BackendAuthToken ?? string.Empty;

                    _pythonProcess = Process.Start(exeStart);
                    if (_pythonProcess == null || _pythonProcess.HasExited)
                    {
                        throw new InvalidOperationException("Não foi possível iniciar o backend empacotado (sisrua_backend.exe).");
                    }
                    PersistBackendPid(_pythonProcess.Id);

                    if (!WaitForBackendHealthy(TimeSpan.FromSeconds(20)))
                    {
                        LogToEditor("\n>>> Aviso: backend empacotado iniciou, mas não respondeu health dentro do tempo limite.");
                    }
                    if (!WaitForBackendAuthorized(TimeSpan.FromSeconds(20)))
                    {
                        LogToEditor("\n>>> Aviso: backend empacotado iniciou, mas não respondeu auth-check dentro do tempo limite.");
                    }

                    LogToEditor("\n>>> Backend do sisRUA (EXE) iniciado com sucesso.");
                    return;
                }

#if !DEBUG
                LogAndAlert("Erro Crítico: sisrua_backend.exe não encontrado.\n\nPara uso em produção, o sisRUA precisa do backend empacotado (EXE).\nReinstale o sisRUA usando o instalador e tente novamente.");
                return;
#else
                // Em Debug, permitimos fallback para Python/venv para facilitar desenvolvimento.
                string pythonExePath = FindPythonExecutable();
                if (string.IsNullOrEmpty(pythonExePath))
                {
                    LogAndAlert("Erro Crítico: O executável do Python ('python.exe') não foi encontrado. Para que o plugin sisRUA funcione, o Python (versão 3.7 ou superior) deve ser instalado. \n\nOpções:\n1. (Recomendado) Instale o Python a partir da Python.org e certifique-se de marcar a opção 'Add Python to PATH' durante a instalação.\n2. Se o Python já estiver instalado, certifique-se de que a pasta contendo 'python.exe' está na variável de ambiente PATH do Windows.\n3. (Avançado) Crie um ambiente virtual na raiz do projeto sisRUA com o nome 'venv'.");
                    return;
                }

                string backendSourceRoot = FindBackendSourceRoot(Path.GetDirectoryName(pluginPath));
                if (string.IsNullOrWhiteSpace(backendSourceRoot))
                {
                    LogAndAlert("Erro Crítico: Não foi possível localizar o código-fonte do backend em src\\backend (modo Debug).");
                    return;
                }

                // Garante que exista um venv local e que as dependências do backend estejam instaladas.
                // Isso evita falhas em máquinas "limpas" que têm Python mas não têm os pacotes (ex.: osmnx).
                pythonExePath = EnsureVenvAndDependencies(backendSourceRoot, pythonExePath);
                if (string.IsNullOrEmpty(pythonExePath))
                {
                    LogAndAlert("Erro Crítico: Não foi possível preparar o ambiente Python (venv + dependências). Verifique o log no console do AutoCAD/Windows e tente novamente.");
                    return;
                }

                var startInfo = new ProcessStartInfo(pythonExePath)
                {
                    Arguments = $"-m uvicorn backend.api:app --host 127.0.0.1 --port {BackendPort}",
                    WorkingDirectory = backendSourceRoot,
                    UseShellExecute = false,
                    CreateNoWindow = false, // Exibir janela do console para depuração
                };
                startInfo.EnvironmentVariables[BackendAuthEnvVarName] = BackendAuthToken ?? string.Empty;

                _pythonProcess = Process.Start(startInfo);

                if (_pythonProcess == null || _pythonProcess.HasExited)
                {
                    throw new InvalidOperationException("Não foi possível iniciar o processo Python. Verifique se o Python está instalado e configurado no PATH do sistema.");
                }

                // Aguarda o backend ficar pronto (poll em /api/v1/health).
                if (!WaitForBackendHealthy(TimeSpan.FromSeconds(20)))
                    LogToEditor("\n>>> Aviso: backend iniciado, mas não respondeu health dentro do tempo limite.");
                if (!WaitForBackendAuthorized(TimeSpan.FromSeconds(20)))
                    LogToEditor("\n>>> Aviso: backend iniciou, mas não respondeu auth-check dentro do tempo limite.");

                LogToEditor("\n>>> Backend do sisRUA (Python) iniciado com sucesso.");
#endif
            }
            catch (System.Exception ex)
            {
                LogAndAlert("Erro durante Initialize(): " + ex.Message);
                _logger?.WriteLine($"[ERROR] Exception during Initialize(): {ex}");
                _pythonProcess = null;
            }
        }

        /// <summary>
        /// Chamado quando o AutoCAD é fechado. Encerra a árvore de processos do backend.
        /// </summary>
        public void Terminate()
        {
            LogToEditor("\n>>> sisRUA Plugin: Terminate() called.");
            try
            {
                if (_pythonProcess != null && !_pythonProcess.HasExited)
                {
                    try
                    {
                        // Usar taskkill com /T é a forma mais segura de garantir que todos os sub-processos
                        // (como o uvicorn worker) sejam encerrados junto com o processo principal.
                        var killInfo = new ProcessStartInfo("taskkill", $"/F /T /PID {_pythonProcess.Id}")
                        {
                            CreateNoWindow = true,
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true
                        };

                        using (var killProcess = Process.Start(killInfo))
                        {
                            killProcess?.WaitForExit(5000); // Aguarda no máximo 5 segundos
                        }
                    }
                    finally
                    {
                        _pythonProcess.Dispose();
                        _pythonProcess = null;
                        LogToEditor("\n>>> Backend do sisRUA finalizado.");
                    }

                    return;
                }

                // Fallback: se o handle não existe (backend reaproveitado), tenta matar o PID persistido.
                TryKillPreviousBackendProcess();
            }
            catch (System.Exception ex)
            {
                LogToEditor($"\n[ERROR] Exceção ao tentar finalizar o backend: {ex.Message}");
                _logger?.WriteLine($"[ERROR] Exception during Terminate(): {ex}");
            }
            finally
            {
                _logger?.Close();
                _logger = null;
            }
        }

        private void SetupLogger()
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return;

                string logDir = Path.Combine(localSisRuaDir, "logs");
                Directory.CreateDirectory(logDir);

                string logFileName = $"sisRUA_plugin_{DateTime.Now:yyyyMMdd_HHmmss}.log";
                string logFilePath = Path.Combine(logDir, logFileName);

                _logger = TextWriter.Synchronized(new StreamWriter(logFilePath, append: true, Encoding.UTF8) { AutoFlush = true });
                SisRuaLog.SetFileLogger(_logger);
                _logger.WriteLine($"--- sisRUA Plugin Log Started: {DateTime.Now} ---");
                _logger.WriteLine($"Plugin Assembly: {Assembly.GetExecutingAssembly().Location}");
                _logger.WriteLine($"AutoCAD Process Id: {Process.GetCurrentProcess().Id}");
            }
            catch (System.Exception ex)
            {
                Debug.WriteLine($"[sisRUA] ERROR: Failed to setup logger: {ex.Message}");
                // Fallback to only editor/debug output if logger setup fails
            }
        }

        private Assembly CurrentDomain_AssemblyResolve(object sender, ResolveEventArgs args)
        {
            _logger?.WriteLine($"[DEBUG] Attempting to resolve assembly: {args.Name}");
            // Pega o nome da DLL que está faltando
            string assemblyName = new AssemblyName(args.Name).Name + ".dll";
            
            // Pega a pasta onde o seu plugin (sisRUA.dll) está instalado
            string assemblyPath = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string fullPath = Path.Combine(assemblyPath, assemblyName);

            // Se a DLL existir na pasta do plugin, carrega ela manualmente
            if (File.Exists(fullPath))
            {
                _logger?.WriteLine($"[DEBUG] Resolved '{args.Name}' from '{fullPath}'");
                return Assembly.LoadFrom(fullPath);
            }
            _logger?.WriteLine($"[DEBUG] Failed to resolve '{args.Name}' from '{fullPath}'");
            return null;
        }

        /// <summary>
        /// Procura recursivamente para cima a partir de um diretório inicial até encontrar
        /// uma pasta que contenha o subdiretório 'backend'.
        /// </summary>
        private string FindProjectRoot(string startPath)
        {
            _logger?.WriteLine($"[DEBUG] FindProjectRoot started from: {startPath}");
            var currentDir = new DirectoryInfo(startPath);
            int sanityCheck = 0; // Evita loop infinito
            while (currentDir != null && sanityCheck < 10)
            {
                // Modo instalado: a DLL roda dentro de Contents\
                if (Directory.Exists(Path.Combine(currentDir.FullName, "backend")))
                {
                    _logger?.WriteLine($"[DEBUG] Found project root (installed mode): {currentDir.FullName}");
                    return currentDir.FullName;
                }

                // Suporte ao layout do bundle mesmo quando o plugin é executado a partir de bin/
                // - Novo layout: bundle-template/sisRUA.bundle/Contents/backend
                string bundleTemplateContents = Path.Combine(currentDir.FullName, "bundle-template", "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(bundleTemplateContents, "backend")))
                {
                    _logger?.WriteLine($"[DEBUG] Found project root (bundle-template mode): {bundleTemplateContents}");
                    return bundleTemplateContents;
                }

                // - Release: release/sisRUA.bundle/Contents/backend
                string releaseContents = Path.Combine(currentDir.FullName, "release", "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(releaseContents, "backend")))
                {
                    _logger?.WriteLine($"[DEBUG] Found project root (release mode): {releaseContents}");
                    return releaseContents;
                }

                // - Compatibilidade (layout antigo): sisRUA.bundle/Contents/backend
                string legacyContents = Path.Combine(currentDir.FullName, "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(legacyContents, "backend")))
                {
                    _logger?.WriteLine($"[DEBUG] Found project root (legacy mode): {legacyContents}");
                    return legacyContents;
                }
                currentDir = currentDir.Parent;
                sanityCheck++;
            }
            _logger?.WriteLine("[DEBUG] FindProjectRoot: No project root found.");
            return null;
        }

        private string FindBackendSourceRoot(string startPath)
        {
            _logger?.WriteLine($"[DEBUG] FindBackendSourceRoot started from: {startPath}");
            var currentDir = new DirectoryInfo(startPath);
            int sanityCheck = 0;
            while (currentDir != null && sanityCheck < 10)
            {
                string candidate = Path.Combine(currentDir.FullName, "src", "backend");
                if (File.Exists(Path.Combine(candidate, "requirements.txt")) &&
                    File.Exists(Path.Combine(candidate, "standalone.py")) &&
                    File.Exists(Path.Combine(candidate, "backend", "api.py")))
                {
                    _logger?.WriteLine($"[DEBUG] Found backend source root: {candidate}");
                    return candidate;
                }
                currentDir = currentDir.Parent;
                sanityCheck++;
            }
            _logger?.WriteLine("[DEBUG] FindBackendSourceRoot: No backend source root found.");
            return null;
        }
        
        private void LogToEditor(string message)
        {
            if (_editor != null)
            {
                _editor.WriteMessage(message);
            }
            Debug.WriteLine($"[sisRUA] {message.Trim()}");
            _logger?.WriteLine($"[INFO] {message.Trim()}");
        }

        private void LogAndAlert(string message)
        {
            LogToEditor($"\n{message}");
            Autodesk.AutoCAD.ApplicationServices.Application.ShowAlertDialog(message);
            _logger?.WriteLine($"[ALERT] {message.Trim()}");
        }

        private string FindPythonExecutable()
        {
            _logger?.WriteLine("[DEBUG] FindPythonExecutable started.");
            // 0. Preferir venv local (AppData) para evitar problemas de permissão/sync (ex.: Google Drive)
            string localSisRuaDir = GetLocalSisRuaDir();
            if (!string.IsNullOrEmpty(localSisRuaDir))
            {
                string localVenvPython = Path.Combine(localSisRuaDir, "venv", "Scripts", "python.exe");
                if (File.Exists(localVenvPython))
                {
                    LogToEditor($"\n>>> Python encontrado no venv local: {localVenvPython}");
                    _logger?.WriteLine($"[DEBUG] Found Python in local venv: {localVenvPython}");
                    return localVenvPython;
                }
            }

            // 1. Check venv in project root first - this is the most likely and desired location
            string pluginPath = Assembly.GetExecutingAssembly().Location;
            string projectRoot = FindProjectRoot(Path.GetDirectoryName(pluginPath));
            if (!string.IsNullOrEmpty(projectRoot))
            {
                string venvPath = Path.Combine(projectRoot, "venv", "Scripts", "python.exe");
                if (File.Exists(venvPath))
                {
                    LogToEditor($"\n>>> Python encontrado no ambiente virtual do projeto: {venvPath}");
                    _logger?.WriteLine($"[DEBUG] Found Python in project venv: {venvPath}");
                    return venvPath;
                }
            }
            
            // 2. Check PATH environment variable
            string pathVar = Environment.GetEnvironmentVariable("PATH");
            if (pathVar != null)
            {
                foreach (string path in pathVar.Split(Path.PathSeparator))
                {
                    try
                    {
                        string potentialPath = Path.Combine(path.Trim(), "python.exe");
                        if (File.Exists(potentialPath))
                        {
                            LogToEditor($"\n>>> Python encontrado no PATH do sistema: {potentialPath}");
                            _logger?.WriteLine($"[DEBUG] Found Python in system PATH: {potentialPath}");
                            return potentialPath;
                        }
                    }
                    catch (ArgumentException) { _logger?.WriteLine($"[DEBUG] Ignored invalid PATH entry: {path}"); /* Ignora caminhos inválidos no PATH */ }
                }
            }

            // 3. Check common installation directories for system-wide installs
            string[] commonPaths = {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", "Python"),
                "C:\\Program Files\\Python",
                "C:\\Python"
            };

            foreach (string basePath in commonPaths)
            {
                if (Directory.Exists(basePath))
                {
                    try
                    {
                        // Search for python.exe in subdirectories like Python39, Python310 etc.
                        foreach (string pythonDir in Directory.GetDirectories(basePath, "Python*"))
                        {
                            string exePath = Path.Combine(pythonDir, "python.exe");
                            if (File.Exists(exePath))
                            {
                                LogToEditor($"\n>>> Python encontrado em diretório de instalação comum: {exePath}");
                                _logger?.WriteLine($"[DEBUG] Found Python in common install dir: {exePath}");
                                return exePath;
                            }
                        }
                    }
                    catch (System.Security.SecurityException ex) { _logger?.WriteLine($"[DEBUG] Ignored inaccessible directory {basePath}: {ex.Message}"); /* Ignora pastas sem permissão de acesso */ }
                }
            }

            _logger?.WriteLine("[DEBUG] FindPythonExecutable: Python executable not found.");
            return null; // Not found
        }

        private string EnsureVenvAndDependencies(string backendSourceRoot, string pythonExePath)
        {
            _logger?.WriteLine($"[DEBUG] EnsureVenvAndDependencies started. Source: {backendSourceRoot}, Python: {pythonExePath}");
            try
            {
                string requirementsPath = Path.Combine(backendSourceRoot, "requirements.txt");
                if (!File.Exists(requirementsPath))
                {
                    LogToEditor($"\n>>> Aviso: requirements.txt não encontrado em '{requirementsPath}'. Usando Python do sistema.");
                    _logger?.WriteLine($"[WARN] requirements.txt not found at {requirementsPath}. Using system Python.");
                    return pythonExePath;
                }

                // Preferimos criar/usar venv em AppData (mais estável que rodar em pastas sincronizadas/sem permissão).
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir))
                {
                    LogToEditor("\n>>> Aviso: não foi possível resolver LocalAppData. Usando venv do projeto (se existir).");
                    _logger?.WriteLine("[WARN] Could not resolve LocalAppData. Using project venv.");
                    localSisRuaDir = backendSourceRoot;
                }

                Directory.CreateDirectory(localSisRuaDir);

                string venvDir = Path.Combine(localSisRuaDir, "venv");
                string venvPython = Path.Combine(venvDir, "Scripts", "python.exe");
                bool venvExists = File.Exists(venvPython);

                if (!venvExists)
                {
                    LogToEditor($"\n>>> Preparando ambiente Python (criando venv local em '{venvDir}')...");
                    _logger?.WriteLine($"[INFO] Creating local venv at {venvDir}...");

                    var (exitCode, stdout, stderr) = RunProcess(pythonExePath, localSisRuaDir, timeoutMs: 10 * 60 * 1000, "-m", "venv", venvDir);
                    if (exitCode != 0 || !File.Exists(venvPython))
                    {
                        // Fallback: em alguns ambientes o ensurepip pode falhar durante a criação do venv.
                        // Nesse caso, criamos sem pip e rodamos ensurepip explicitamente.
                        LogToEditor($"\n>>> Aviso: criação padrão do venv falhou. Tentando fallback (--without-pip).\nExitCode={exitCode}\n{stdout}\n{stderr}");
                        _logger?.WriteLine($"[WARN] Venv creation failed (exitCode={exitCode}). Trying fallback (--without-pip). Stdout: {stdout}, Stderr: {stderr}");

                        try
                        {
                            if (Directory.Exists(venvDir))
                            {
                                Directory.Delete(venvDir, recursive: true);
                            }
                        }
                        catch (System.Exception ex) { _logger?.WriteLine($"[DEBUG] Error cleaning up venv dir: {ex.Message}"); /* ignore cleanup errors */ }

                        var (exitCode2, stdout2, stderr2) = RunProcess(pythonExePath, localSisRuaDir, timeoutMs: 10 * 60 * 1000, "-m", "venv", "--without-pip", venvDir);
                        if (exitCode2 != 0 || !File.Exists(venvPython))
                        {
                            LogToEditor($"\n>>> ERRO: falha ao criar venv (fallback). ExitCode={exitCode2}\n{stdout2}\n{stderr2}");
                            _logger?.WriteLine($"[ERROR] Venv creation (fallback) failed (exitCode={exitCode2}). Stdout: {stdout2}, Stderr: {stderr2}");
                            return null;
                        }

                        var (exitCode3, stdout3, stderr3) = RunProcess(venvPython, localSisRuaDir, timeoutMs: 10 * 60 * 1000, "-m", "ensurepip", "--upgrade");
                        if (exitCode3 != 0)
                        {
                            LogToEditor($"\n>>> ERRO: falha ao habilitar pip no venv (ensurepip). ExitCode={exitCode3}\n{stdout3}\n{stderr3}");
                            _logger?.WriteLine($"[ERROR] Ensurepip failed (exitCode={exitCode3}). Stdout: {stdout3}, Stderr: {stderr3}");
                            return null;
                        }
                    }
                }

                // Verifica se os pacotes principais importam.
                if (!TryPythonImport(venvPython, "fastapi,uvicorn,osmnx,pyproj,shapely", backendSourceRoot))
                {
                    LogToEditor("\n>>> Instalando dependências do backend no venv (primeira execução pode demorar)...");
                    _logger?.WriteLine("[INFO] Installing backend dependencies...");

                    // Upgrade pip ajuda a evitar problemas comuns com wheels.
                    RunProcess(venvPython, backendSourceRoot, timeoutMs: 10 * 60 * 1000, "-m", "pip", "install", "--upgrade", "pip");

                    var (exitCode, stdout, stderr) = RunProcess(
                        venvPython,
                        backendSourceRoot,
                        timeoutMs: 20 * 60 * 1000,
                        "-m", "pip", "install", "-r", requirementsPath
                    );

                    if (exitCode != 0)
                    {
                        LogToEditor($"\n>>> ERRO: falha ao instalar requirements. ExitCode={exitCode}\n{stdout}\n{stderr}");
                        _logger?.WriteLine($"[ERROR] Requirements installation failed (exitCode={exitCode}). Stdout: {stdout}, Stderr: {stderr}");
                        return null;
                    }

                    if (!TryPythonImport(venvPython, "fastapi,uvicorn,osmnx", backendSourceRoot))
                    {
                        LogToEditor("\n>>> ERRO: dependências ainda não importam após instalação.");
                        _logger?.WriteLine("[ERROR] Dependencies still not importable after installation.");
                        return null;
                    }
                }

                LogToEditor($"\n>>> Ambiente Python pronto: {venvPython}");
                _logger?.WriteLine($"[INFO] Python environment ready: {venvPython}");
                return venvPython;
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in EnsureVenvAndDependencies: {ex}");
                return null;
            }
        }

        public static string GetLocalSisRuaDir()
        {
            try
            {
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrWhiteSpace(localAppData)) return null;
                return Path.Combine(localAppData, "sisRUA");
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in GetLocalSisRuaDir: {ex}");
                return null;
            }
        }

        private static int ChooseFreePort()
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            listener.Start();
            int port = ((IPEndPoint)listener.LocalEndpoint).Port;
            listener.Stop();
            return port;
        }

        private int TryReadLastBackendPort()
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return 0;
                string statePath = Path.Combine(localSisRuaDir, "backend_port.txt");
                if (!File.Exists(statePath)) return 0;
                string text = File.ReadAllText(statePath)?.Trim();
                int.TryParse(text, out int p); // Use the return value of TryParse
                _logger?.WriteLine($"[DEBUG] Read last backend port: {p}");
                return p;
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in TryReadLastBackendPort: {ex}");
                return 0;
            }
        }

        private string TryReadLastBackendToken()
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return null;
                string statePath = Path.Combine(localSisRuaDir, "backend_token.txt");
                if (!File.Exists(statePath)) return null;
                string token = File.ReadAllText(statePath)?.Trim();
                _logger?.WriteLine($"[DEBUG] Read last backend token (hash): {token?.GetHashCode()}");
                return token;
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in TryReadLastBackendToken: {ex}");
                return null;
            }
        }

        private void PersistBackendPort(int port)
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return;
                Directory.CreateDirectory(localSisRuaDir);
                string statePath = Path.Combine(localSisRuaDir, "backend_port.txt");
                File.WriteAllText(statePath, port.ToString());
                _logger?.WriteLine($"[DEBUG] Persisted backend port: {port}");
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in PersistBackendPort: {ex}");
            }
        }

        private void PersistBackendToken(string token)
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return;
                Directory.CreateDirectory(localSisRuaDir);
                string statePath = Path.Combine(localSisRuaDir, "backend_token.txt");
                File.WriteAllText(statePath, token ?? string.Empty);
                _logger?.WriteLine($"[DEBUG] Persisted backend token (hash): {token?.GetHashCode()}");
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in PersistBackendToken: {ex}");
            }
        }

        private void PersistBackendPid(int pid)
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return;
                Directory.CreateDirectory(localSisRuaDir);
                string statePath = Path.Combine(localSisRuaDir, "backend_pid.txt");
                File.WriteAllText(statePath, pid.ToString());
                _logger?.WriteLine($"[DEBUG] Persisted backend PID: {pid}");
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in PersistBackendPid: {ex}");
            }
        }

        private int TryReadLastBackendPid()
        {
            try
            {
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir)) return 0;
                string statePath = Path.Combine(localSisRuaDir, "backend_pid.txt");
                if (!File.Exists(statePath)) return 0;
                string text = File.ReadAllText(statePath)?.Trim();
                int.TryParse(text, out int p); // Use the return value of TryParse
                _logger?.WriteLine($"[DEBUG] Read last backend PID: {p}");
                return p;
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in TryReadLastBackendPid: {ex}");
                return 0;
            }
        }

        private void TryKillPreviousBackendProcess()
        {
            _logger?.WriteLine("[DEBUG] TryKillPreviousBackendProcess started.");
            try
            {
                int pid = TryReadLastBackendPid();
                if (pid <= 0) return;

                Process p = Process.GetProcessById(pid);
                string name = p.ProcessName?.ToLowerInvariant() ?? string.Empty;
                if (name.Contains("sisrua_backend") || name == "python" || name == "pythonw")
                {
                    _logger?.WriteLine($"[INFO] Attempting to kill previous backend process with PID: {pid} (Name: {name})");
                    try
                    {
                        var killInfo = new ProcessStartInfo("taskkill", $"/F /T /PID {pid}")
                        {
                            CreateNoWindow = true,
                            UseShellExecute = false,
                            RedirectStandardOutput = true,
                            RedirectStandardError = true
                        };

                        using (var killProcess = Process.Start(killInfo))
                        {
                            killProcess?.WaitForExit(5000);
                        }
                        _logger?.WriteLine($"[INFO] Successfully killed process PID {pid}.");
                    }
                    catch (System.Exception ex)
                    {
                        _logger?.WriteLine($"[ERROR] Error killing process PID {pid}: {ex.Message}");
                    }
                }
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Exception in TryKillPreviousBackendProcess: {ex}");
            }
        }

        private void AttachToExistingProcess()
        {
            int previousPid = TryReadLastBackendPid();
            if (previousPid > 0)
            {
                try
                {
                    _pythonProcess = Process.GetProcessById(previousPid);
                }
                catch
                {
                    _pythonProcess = null;
                }
            }
        }

        private void TryKillProcess(int pid)
        {
            try
            {
                var killInfo = new ProcessStartInfo("taskkill", $"/F /T /PID {pid}")
                {
                    CreateNoWindow = true, UseShellExecute = false, RedirectStandardOutput = true, RedirectStandardError = true
                };
                using (var p = Process.Start(killInfo)) { p?.WaitForExit(5000); }
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[ERROR] Failed to kill PID {pid}: {ex.Message}");
            }
        }

        private bool IsBackendHealthy()
        {
            try
            {
                if (string.IsNullOrWhiteSpace(BackendBaseUrl)) return false;
                var resp = _healthClient.GetAsync($"{BackendBaseUrl}/api/v1/health").GetAwaiter().GetResult();
                _logger?.WriteLine($"[DEBUG] Backend health check to {BackendBaseUrl}/api/v1/health: {resp.IsSuccessStatusCode}");
                return resp.IsSuccessStatusCode;
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[WARN] Backend health check failed: {ex.Message}");
                return false;
            }
        }

        private bool IsBackendAuthorized()
        {
            try
            {
                if (string.IsNullOrWhiteSpace(BackendBaseUrl)) return false;
                if (string.IsNullOrWhiteSpace(BackendAuthToken)) return false;

                using (var req = new HttpRequestMessage(HttpMethod.Get, $"{BackendBaseUrl}/api/v1/auth/check"))
                {
                    req.Headers.TryAddWithoutValidation(BackendAuthHeaderName, BackendAuthToken);
                    var resp = _healthClient.SendAsync(req).GetAwaiter().GetResult();
                    _logger?.WriteLine($"[DEBUG] Backend auth check to {BackendBaseUrl}/api/v1/auth/check: {resp.IsSuccessStatusCode}");
                    return resp.IsSuccessStatusCode;
                }
            }
            catch (System.Exception ex)
            {
                _logger?.WriteLine($"[WARN] Backend auth check failed: {ex.Message}");
                return false;
            }
        }

        private bool WaitForBackendHealthy(TimeSpan timeout)
        {
            var sw = Stopwatch.StartNew();
            while (sw.Elapsed < timeout)
            {
                if (IsBackendHealthy()) return true;
                Thread.Sleep(250);
            }
            _logger?.WriteLine($"[WARN] WaitForBackendHealthy timed out after {timeout.TotalSeconds}s.");
            return false;
        }

        private bool WaitForBackendAuthorized(TimeSpan timeout)
        {
            var sw = Stopwatch.StartNew();
            while (sw.Elapsed < timeout)
            {
                if (IsBackendAuthorized()) return true;
                Thread.Sleep(250);
            }
            _logger?.WriteLine($"[WARN] WaitForBackendAuthorized timed out after {timeout.TotalSeconds}s.");
            return false;
        }

        private bool TryPythonImport(string pythonExe, string importList, string workingDirectory)
        {
            _logger?.WriteLine($"[DEBUG] TryPythonImport: {importList} using {pythonExe} in {workingDirectory}");
            // Importa uma lista (ex.: "fastapi,uvicorn,osmnx") dentro do interpretador indicado.
            string code = $"import {importList}; print('OK')";
            var (exitCode, stdout, stderr) = RunProcess(pythonExe, workingDirectory: workingDirectory, timeoutMs: 60 * 1000, "-c", code);
            _logger?.WriteLine($"[DEBUG] TryPythonImport exitCode: {exitCode}. Stdout: {stdout}. Stderr: {stderr}.");
            return exitCode == 0;
        }

        private (int exitCode, string stdout, string stderr) RunProcess(string fileName, string workingDirectory, int timeoutMs, params string[] argumentList)
        {
            _logger?.WriteLine($"[DEBUG] Running process: {fileName} {BuildCommandLine(argumentList)} in {workingDirectory}");
            var psi = new ProcessStartInfo(fileName)
            {
                WorkingDirectory = workingDirectory,
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true
            };

            psi.Arguments = BuildCommandLine(argumentList);

            using (var p = new Process { StartInfo = psi })
            {
                var stdout = new StringBuilder();
                var stderr = new StringBuilder();

                p.OutputDataReceived += (_, e) => { if (e.Data != null) stdout.AppendLine(e.Data); };
                p.ErrorDataReceived += (_, e) => { if (e.Data != null) stderr.AppendLine(e.Data); };

                p.Start();
                p.BeginOutputReadLine();
                p.BeginErrorReadLine();

                bool exited = p.WaitForExit(timeoutMs);
                if (!exited)
                {
                    try { p.Kill(); } catch (System.Exception ex) { _logger?.WriteLine($"[ERROR] Error killing timed-out process: {ex.Message}"); }
                    _logger?.WriteLine($"[ERROR] Process timed out. Filename: {fileName}");
                    return (-1, stdout.ToString(), "Timeout ao executar processo.");
                }

                _logger?.WriteLine($"[DEBUG] Process exited with code {p.ExitCode}. Filename: {fileName}.");
                return (p.ExitCode, stdout.ToString(), stderr.ToString());
            }
        }

        private static string BuildCommandLine(params string[] args)
        {
            if (args == null || args.Length == 0) return string.Empty;
            var sb = new StringBuilder();
            foreach (var raw in args)
            {
                if (sb.Length > 0) sb.Append(' ');
                sb.Append(QuoteArg(raw ?? string.Empty));
            }
            return sb.ToString();
        }

        private static string QuoteArg(string arg)
        {
            if (arg == null) return "\"\"";
            bool needsQuotes = arg.Length == 0 || arg.IndexOfAny(new[] { ' ', '\t', '\n', '\v', '"' }) >= 0;
            if (!needsQuotes) return arg;
            return "\"" + arg.Replace("\"", "\\\"") + "\"";
        }
    }
}