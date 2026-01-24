using Autodesk.AutoCAD.ApplicationServices;
using Autodesk.AutoCAD.ApplicationServices.Core;
using Autodesk.AutoCAD.EditorInput;
using Autodesk.AutoCAD.Runtime;
using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;

[assembly: ExtensionApplication(typeof(sisRUA.SisRuaPlugin))]

namespace sisRUA
{
    /// <summary>
    /// Gerencia o ciclo de vida do processo de backend Python (servidor FastAPI).
    /// </summary>
    public class SisRuaPlugin : IExtensionApplication
    {
        private Process _pythonProcess;
        private static Editor _editor => Autodesk.AutoCAD.ApplicationServices.Application.DocumentManager.MdiActiveDocument?.Editor;

        /// <summary>
        /// Chamado quando o AutoCAD carrega a extensão.
        /// Localiza e inicia o servidor Python de forma robusta.
        /// </summary>
        public void Initialize()
        {
            try
            {
                string pluginPath = Assembly.GetExecutingAssembly().Location;
                string projectRoot = FindProjectRoot(Path.GetDirectoryName(pluginPath));

                if (string.IsNullOrEmpty(projectRoot))
                {
                    LogAndAlert("Erro Crítico: Não foi possível localizar a pasta raiz do sisRUA contendo o diretório 'backend'. O plugin não funcionará.");
                    return;
                }

                string apiScriptPath = Path.Combine(projectRoot, "backend", "api.py");
                if (!File.Exists(apiScriptPath))
                {
                    LogAndAlert($"Erro Crítico: O arquivo 'api.py' não foi encontrado em '{Path.Combine(projectRoot, "backend")}'. O plugin não funcionará.");
                    return;
                }
                
                string pythonExePath = FindPythonExecutable();
                if (string.IsNullOrEmpty(pythonExePath))
                {
                    LogAndAlert("Erro Crítico: O executável do Python ('pythonw.exe') não foi encontrado. Para que o plugin sisRUA funcione, o Python (versão 3.7 ou superior) deve ser instalado. \n\nOpções:\n1. (Recomendado) Instale o Python a partir da Python.org e certifique-se de marcar a opção 'Add Python to PATH' durante a instalação.\n2. Se o Python já estiver instalado, certifique-se de que a pasta contendo 'pythonw.exe' está na variável de ambiente PATH do Windows.\n3. (Avançado) Crie um ambiente virtual na raiz do projeto sisRUA com o nome 'venv'.");
                    return;
                }

                // Usar 'pythonw.exe' é preferível para processos de background sem console.
                var startInfo = new ProcessStartInfo(pythonExePath)
                {
                    Arguments = $"-m uvicorn backend.api:app --host 127.0.0.1 --port 8000",
                    WorkingDirectory = projectRoot,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                };

                _pythonProcess = Process.Start(startInfo);

                if (_pythonProcess == null || _pythonProcess.HasExited)
                {
                    throw new InvalidOperationException("Não foi possível iniciar o processo Python. Verifique se o Python está instalado e configurado no PATH do sistema.");
                }

                // Uma pequena pausa para dar tempo ao servidor de iniciar antes que o usuário tente usá-lo.
                System.Threading.Thread.Sleep(1500); 

                LogToEditor("\n>>> Backend do sisRUA (Python) iniciado com sucesso.");
            }
            catch (System.Exception ex)
            {
                LogAndAlert($"Falha catastrófica ao iniciar o backend do sisRUA: {ex.Message}");
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
                if (Directory.Exists(Path.Combine(currentDir.FullName, "backend")))
                {
                    return currentDir.FullName;
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
            // 1. Check venv in project root first - this is the most likely and desired location
            string pluginPath = Assembly.GetExecutingAssembly().Location;
            string projectRoot = FindProjectRoot(Path.GetDirectoryName(pluginPath));
            if (!string.IsNullOrEmpty(projectRoot))
            {
                string venvPath = Path.Combine(projectRoot, "venv", "Scripts", "pythonw.exe");
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
                        string potentialPath = Path.Combine(path.Trim(), "pythonw.exe");
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
                        // Search for pythonw.exe in subdirectories like Python39, Python310 etc.
                        foreach (string pythonDir in Directory.GetDirectories(basePath, "Python*"))
                        {
                            string exePath = Path.Combine(pythonDir, "pythonw.exe");
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
    }
}
