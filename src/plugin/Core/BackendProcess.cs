// Core/BackendProcess.cs (partial BackendManager)
// Responsabilidade: spawn de processo EXE/Python, IPC Named Pipe e kill.
// Orquestração em BackendManager.cs; persistência em BackendPersistence.cs.
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading;

namespace sisRUA.Core
{
    public partial class BackendManager
    {
        private void StartExeBackend(string exePath, string workDir)
        {
            Log($"Iniciando backend empacotado na porta {Port}...");
            var psi = new ProcessStartInfo(exePath)
            {
                WorkingDirectory = workDir,
                UseShellExecute = false,
                CreateNoWindow = true,
                WindowStyle = ProcessWindowStyle.Hidden,
                Arguments = $"--host 127.0.0.1 --port {Port} --log-level warning"
            };
            // Secure IPC: Token is retrieved via Named Pipe, not env-var.

            _pythonProcess = Process.Start(psi);
            if (_pythonProcess == null || _pythonProcess.HasExited)
                throw new InvalidOperationException("Falha ao iniciar sisrua_backend.exe");

            PersistBackendPid(_pythonProcess.Id);

            if (WaitForPipeServer(TimeSpan.FromSeconds(45)))
            {
                string token = GetTokenFromIpc();
                if (!string.IsNullOrEmpty(token))
                {
                    AuthToken = token;
                    PersistBackendToken(AuthToken);
                    Log("Token recuperado com sucesso via Secure IPC (EXE).");
                }
                else
                {
                    Log("[ERROR] Falha ao recuperar token via IPC mesmo com servidor de pipe ativo.");
                }
            }
            else
            {
                Log("[ERROR] Timeout aguardando Servidor de Pipe (IPC) do Backend EXE.");
            }

            if (!WaitForBackendHealthy(TimeSpan.FromSeconds(60)))
                Log("[ERROR] Backend (EXE) iniciou mas health check falhou após 60s.");
        }

        private void StartPythonBackend(string projectRoot)
        {
            string pythonExe = FindPythonExecutable();
            if (string.IsNullOrEmpty(pythonExe))
            {
                Alert("Python não encontrado para modo Debug.");
                return;
            }

            string srcRoot = FindBackendSourceRoot(projectRoot);
            pythonExe = EnsureVenvAndDependencies(srcRoot, pythonExe);

            var psi = new ProcessStartInfo(pythonExe)
            {
                Arguments = $"-m uvicorn backend.api:app --host 127.0.0.1 --port {Port}",
                WorkingDirectory = srcRoot,
                UseShellExecute = false,
                CreateNoWindow = false
            };
            // Secure IPC: Token is retrieved via Named Pipe, not env-var.

            _pythonProcess = Process.Start(psi);
            PersistBackendPid(_pythonProcess.Id);

            if (!WaitForPipeServer(TimeSpan.FromSeconds(45)))
            {
                Log("[Aviso] IPC Pipe não disponível após 45s. Tentando fallback ou aguardando HTTP...");
            }
            else
            {
                string token = GetTokenFromIpc();
                if (!string.IsNullOrEmpty(token))
                {
                    AuthToken = token;
                    PersistBackendToken(AuthToken);
                    Log("Token recuperado com sucesso via Secure IPC.");
                }
                else
                {
                    Log("[ERROR] Falha ao recuperar token via IPC.");
                }
            }

            if (!WaitForBackendHealthy(TimeSpan.FromSeconds(60)))
                Log("[ERROR] Backend (Python) iniciou mas health check falhou após 60s.");
        }

        private bool WaitForPipeServer(TimeSpan timeout)
        {
            var sw = Stopwatch.StartNew();
            while (sw.Elapsed < timeout)
            {
                try
                {
                    using (var client = new System.IO.Pipes.NamedPipeClientStream(".", "sisrua_backend", System.IO.Pipes.PipeDirection.InOut))
                    {
                        client.Connect(100);
                        return true;
                    }
                }
                catch { Thread.Sleep(500); }
            }
            return false;
        }

        private string GetTokenFromIpc()
        {
            try
            {
                using (var client = new System.IO.Pipes.NamedPipeClientStream(".", "sisrua_backend", System.IO.Pipes.PipeDirection.InOut))
                {
                    client.Connect(2000);
                    byte[] request = Encoding.UTF8.GetBytes("GET_TOKEN");
                    client.Write(request, 0, request.Length);

                    byte[] buffer = new byte[4096];
                    int bytesRead = client.Read(buffer, 0, buffer.Length);
                    return Encoding.UTF8.GetString(buffer, 0, bytesRead);
                }
            }
            catch (Exception ex)
            {
                Log($"Erro no Secure IPC: {ex.Message}");
                return null;
            }
        }

        private void KillProcessTree(int pid)
        {
            var psi = new ProcessStartInfo("taskkill", $"/F /T /PID {pid}")
            {
                CreateNoWindow = true,
                UseShellExecute = false
            };
            Process.Start(psi)?.WaitForExit(5000);
        }

        private string FindPythonExecutable()
        {
            string pathVar = Environment.GetEnvironmentVariable("PATH");
            if (pathVar != null)
            {
                foreach (string dir in pathVar.Split(Path.PathSeparator))
                {
                    try
                    {
                        string pythonExePath = Path.Combine(dir.Trim(), "python.exe");
                        if (File.Exists(pythonExePath)) return pythonExePath;
                    }
                    catch { }
                }
            }
            return null;
        }

        private string EnsureVenvAndDependencies(string srcRoot, string pythonExe)
        {
            // TODO: detect/create venv and run pip install when not in a bundle
            return pythonExe;
        }
    }
}
