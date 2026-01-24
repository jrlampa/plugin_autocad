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

                lock (_backendLock)
                {
                    // Se o backend já estiver rodando, não iniciamos um novo processo.
                    // - Primeiro tenta reaproveitar a última porta salva (se existir).
                    int previousPort = TryReadLastBackendPort();
                    if (previousPort > 0)
                    {
                        BackendPort = previousPort;
                    }

                    string previousToken = TryReadLastBackendToken();
                    if (!string.IsNullOrWhiteSpace(previousToken))
                    {
                        BackendAuthToken = previousToken;
                    }

                    if (string.IsNullOrWhiteSpace(BackendAuthToken))
                    {
                        BackendAuthToken = Guid.NewGuid().ToString("N");
                        PersistBackendToken(BackendAuthToken);
                    }

                    if (IsBackendHealthy() && IsBackendAuthorized())
                    {
                        LogToEditor($"\n>>> Backend do sisRUA já está rodando (health/auth OK) em {BackendBaseUrl}.");
                        return;
                    }

                    // Se estiver saudável, mas não autorizado (token diferente), tenta finalizar o processo anterior.
                    if (IsBackendHealthy() && !IsBackendAuthorized())
                    {
                        TryKillPreviousBackendProcess();
                    }

                    // Porta dinâmica: escolhe uma porta livre para evitar conflito.
                    BackendPort = ChooseFreePort();
                    PersistBackendPort(BackendPort);

                    // Novo token por sessão (persistido para reconexão no mesmo host).
                    BackendAuthToken = Guid.NewGuid().ToString("N");
                    PersistBackendToken(BackendAuthToken);
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
                {
                    LogToEditor("\n>>> Aviso: backend iniciado, mas não respondeu health dentro do tempo limite.");
                }
                if (!WaitForBackendAuthorized(TimeSpan.FromSeconds(20)))
                {
                    LogToEditor("\n>>> Aviso: backend iniciou, mas não respondeu auth-check dentro do tempo limite.");
                }

                LogToEditor("\n>>> Backend do sisRUA (Python) iniciado com sucesso.");
#endif
            }
            catch (System.Exception ex)
            {
                LogAndAlert("Erro ao ligar Python: " + ex.Message);
                _pythonProcess = null;
            }
        }

        /// <summary>
        /// Chamado quando o AutoCAD é fechado. Encerra a árvore de processos do backend.
        /// </summary>
        public void Terminate()
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
                catch (System.Exception ex)
                {
                     Debug.WriteLine($"[sisRUA] Exceção ao tentar finalizar a árvore de processos do backend: {ex.Message}");
                }
                finally
                {
                    _pythonProcess.Dispose();
                    _pythonProcess = null;
                    LogToEditor("\n>>> Backend do sisRUA finalizado.");
                }
            }
        }

        private Assembly CurrentDomain_AssemblyResolve(object sender, ResolveEventArgs args)
        {
            // Pega o nome da DLL que está faltando
            string assemblyName = new AssemblyName(args.Name).Name + ".dll";
            
            // Pega a pasta onde o seu plugin (sisRUA.dll) está instalado
            string assemblyPath = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string fullPath = Path.Combine(assemblyPath, assemblyName);

            // Se a DLL existir na pasta do plugin, carrega ela manualmente
            if (File.Exists(fullPath))
            {
                return Assembly.LoadFrom(fullPath);
            }
            return null;
        }

        /// <summary>
        /// Procura recursivamente para cima a partir de um diretório inicial até encontrar
        /// uma pasta que contenha o subdiretório 'backend'.
        /// </summary>
        private string FindProjectRoot(string startPath)
        {
            var currentDir = new DirectoryInfo(startPath);
            int sanityCheck = 0; // Evita loop infinito
            while (currentDir != null && sanityCheck < 10)
            {
                // Modo instalado: a DLL roda dentro de Contents\
                if (Directory.Exists(Path.Combine(currentDir.FullName, "backend")))
                {
                    return currentDir.FullName;
                }

                // Suporte ao layout do bundle mesmo quando o plugin é executado a partir de bin/
                // - Novo layout: bundle-template/sisRUA.bundle/Contents/backend
                string bundleTemplateContents = Path.Combine(currentDir.FullName, "bundle-template", "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(bundleTemplateContents, "backend")))
                {
                    return bundleTemplateContents;
                }

                // - Release: release/sisRUA.bundle/Contents/backend
                string releaseContents = Path.Combine(currentDir.FullName, "release", "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(releaseContents, "backend")))
                {
                    return releaseContents;
                }

                // - Compatibilidade (layout antigo): sisRUA.bundle/Contents/backend
                string legacyContents = Path.Combine(currentDir.FullName, "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(legacyContents, "backend")))
                {
                    return legacyContents;
                }
                currentDir = currentDir.Parent;
                sanityCheck++;
            }
            return null;
        }

        private string FindBackendSourceRoot(string startPath)
        {
            var currentDir = new DirectoryInfo(startPath);
            int sanityCheck = 0;
            while (currentDir != null && sanityCheck < 10)
            {
                string candidate = Path.Combine(currentDir.FullName, "src", "backend");
                if (File.Exists(Path.Combine(candidate, "requirements.txt")) &&
                    File.Exists(Path.Combine(candidate, "standalone.py")) &&
                    File.Exists(Path.Combine(candidate, "backend", "api.py")))
                {
                    return candidate;
                }
                currentDir = currentDir.Parent;
                sanityCheck++;
            }
            return null;
        }
        
        private void LogToEditor(string message)
        {
            if (_editor != null)
            {
                _editor.WriteMessage(message);
            }
            Debug.WriteLine($"[sisRUA] {message.Trim()}");
        }

        private void LogAndAlert(string message)
        {
            LogToEditor($"\n{message}");
            Autodesk.AutoCAD.ApplicationServices.Application.ShowAlertDialog(message);
        }

        private string FindPythonExecutable()
        {
            // 0. Preferir venv local (AppData) para evitar problemas de permissão/sync (ex.: Google Drive)
            string localSisRuaDir = GetLocalSisRuaDir();
            if (!string.IsNullOrEmpty(localSisRuaDir))
            {
                string localVenvPython = Path.Combine(localSisRuaDir, "venv", "Scripts", "python.exe");
                if (File.Exists(localVenvPython))
                {
                    LogToEditor($"\n>>> Python encontrado no venv local: {localVenvPython}");
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
                            return potentialPath;
                        }
                    }
                    catch (ArgumentException) { /* Ignora caminhos inválidos no PATH */ }
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
                                return exePath;
                            }
                        }
                    }
                    catch (System.Security.SecurityException) { /* Ignora pastas sem permissão de acesso */ }
                }
            }

            return null; // Not found
        }

        private string EnsureVenvAndDependencies(string backendSourceRoot, string pythonExePath)
        {
            try
            {
                string requirementsPath = Path.Combine(backendSourceRoot, "requirements.txt");
                if (!File.Exists(requirementsPath))
                {
                    LogToEditor($"\n>>> Aviso: requirements.txt não encontrado em '{requirementsPath}'. Usando Python do sistema.");
                    return pythonExePath;
                }

                // Preferimos criar/usar venv em AppData (mais estável que rodar em pastas sincronizadas/sem permissão).
                string localSisRuaDir = GetLocalSisRuaDir();
                if (string.IsNullOrEmpty(localSisRuaDir))
                {
                    LogToEditor("\n>>> Aviso: não foi possível resolver LocalAppData. Usando venv do projeto (se existir).");
                    localSisRuaDir = backendSourceRoot;
                }

                Directory.CreateDirectory(localSisRuaDir);

                string venvDir = Path.Combine(localSisRuaDir, "venv");
                string venvPython = Path.Combine(venvDir, "Scripts", "python.exe");
                bool venvExists = File.Exists(venvPython);

                if (!venvExists)
                {
                    LogToEditor($"\n>>> Preparando ambiente Python (criando venv local em '{venvDir}')...");

                    var (exitCode, stdout, stderr) = RunProcess(pythonExePath, localSisRuaDir, timeoutMs: 10 * 60 * 1000, "-m", "venv", venvDir);
                    if (exitCode != 0 || !File.Exists(venvPython))
                    {
                        // Fallback: em alguns ambientes o ensurepip pode falhar durante a criação do venv.
                        // Nesse caso, criamos sem pip e rodamos ensurepip explicitamente.
                        LogToEditor($"\n>>> Aviso: criação padrão do venv falhou. Tentando fallback (--without-pip).\nExitCode={exitCode}\n{stdout}\n{stderr}");

                        try
                        {
                            if (Directory.Exists(venvDir))
                            {
                                Directory.Delete(venvDir, recursive: true);
                            }
                        }
                        catch { /* ignore cleanup errors */ }

                        var (exitCode2, stdout2, stderr2) = RunProcess(pythonExePath, localSisRuaDir, timeoutMs: 10 * 60 * 1000, "-m", "venv", "--without-pip", venvDir);
                        if (exitCode2 != 0 || !File.Exists(venvPython))
                        {
                            LogToEditor($"\n>>> ERRO: falha ao criar venv (fallback). ExitCode={exitCode2}\n{stdout2}\n{stderr2}");
                            return null;
                        }

                        var (exitCode3, stdout3, stderr3) = RunProcess(venvPython, localSisRuaDir, timeoutMs: 10 * 60 * 1000, "-m", "ensurepip", "--upgrade");
                        if (exitCode3 != 0)
                        {
                            LogToEditor($"\n>>> ERRO: falha ao habilitar pip no venv (ensurepip). ExitCode={exitCode3}\n{stdout3}\n{stderr3}");
                            return null;
                        }
                    }
                }

                // Verifica se os pacotes principais importam.
                if (!TryPythonImport(venvPython, "fastapi,uvicorn,osmnx,pyproj,shapely", backendSourceRoot))
                {
                    LogToEditor("\n>>> Instalando dependências do backend no venv (primeira execução pode demorar)...");

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
                        return null;
                    }

                    if (!TryPythonImport(venvPython, "fastapi,uvicorn,osmnx", backendSourceRoot))
                    {
                        LogToEditor("\n>>> ERRO: dependências ainda não importam após instalação.");
                        return null;
                    }
                }

                LogToEditor($"\n>>> Ambiente Python pronto: {venvPython}");
                return venvPython;
            }
            catch (System.Exception ex)
            {
                Debug.WriteLine($"[sisRUA] Exceção em EnsureVenvAndDependencies: {ex}");
                return null;
            }
        }

        private static string GetLocalSisRuaDir()
        {
            try
            {
                string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
                if (string.IsNullOrWhiteSpace(localAppData)) return null;
                return Path.Combine(localAppData, "sisRUA");
            }
            catch
            {
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
                return int.TryParse(text, out int p) ? p : 0;
            }
            catch
            {
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
                return File.ReadAllText(statePath)?.Trim();
            }
            catch
            {
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
            }
            catch
            {
                // ignore
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
            }
            catch
            {
                // ignore
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
            }
            catch
            {
                // ignore
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
                return int.TryParse(text, out int p) ? p : 0;
            }
            catch
            {
                return 0;
            }
        }

        private void TryKillPreviousBackendProcess()
        {
            try
            {
                int pid = TryReadLastBackendPid();
                if (pid <= 0) return;

                Process p = Process.GetProcessById(pid);
                string name = p.ProcessName?.ToLowerInvariant() ?? string.Empty;
                if (name.Contains("sisrua_backend") || name == "python" || name == "pythonw")
                {
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
                    }
                    catch
                    {
                        // ignore
                    }
                }
            }
            catch
            {
                // ignore
            }
        }

        private bool IsBackendHealthy()
        {
            try
            {
                if (string.IsNullOrWhiteSpace(BackendBaseUrl)) return false;
                var resp = _healthClient.GetAsync($"{BackendBaseUrl}/api/v1/health").GetAwaiter().GetResult();
                return resp.IsSuccessStatusCode;
            }
            catch
            {
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
                    return resp.IsSuccessStatusCode;
                }
            }
            catch
            {
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
            return false;
        }

        private bool TryPythonImport(string pythonExe, string importList, string workingDirectory)
        {
            // Importa uma lista (ex.: "fastapi,uvicorn,osmnx") dentro do interpretador indicado.
            string code = $"import {importList}; print('OK')";
            var (exitCode, _, _) = RunProcess(pythonExe, workingDirectory: workingDirectory, timeoutMs: 60 * 1000, "-c", code);
            return exitCode == 0;
        }

        private (int exitCode, string stdout, string stderr) RunProcess(string fileName, string workingDirectory, int timeoutMs, params string[] argumentList)
        {
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
                    try { p.Kill(); } catch { /* ignore */ }
                    return (-1, stdout.ToString(), "Timeout ao executar processo.");
                }

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