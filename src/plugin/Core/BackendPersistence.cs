// Core/BackendPersistence.cs (partial BackendManager)
// Responsabilidade: localização de caminhos, leitura/escrita em disco
// e seleção de porta TCP livre.
// Orquestração em BackendManager.cs; processo em BackendProcess.cs.
using System;
using System.IO;
using System.Net;
using System.Net.Sockets;

namespace sisRUA.Core
{
    public partial class BackendManager
    {
        // --- Path Helpers ---

        private string FindProjectRoot(string startPath)
        {
            var currentDir = new DirectoryInfo(startPath);
            int sanityCheck = 0;
            while (currentDir != null && sanityCheck < 10)
            {
                if (Directory.Exists(Path.Combine(currentDir.FullName, "backend")))
                    return currentDir.FullName;

                string bundle = Path.Combine(currentDir.FullName, "bundle-template", "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(bundle, "backend"))) return bundle;

                string legacy = Path.Combine(currentDir.FullName, "sisRUA.bundle", "Contents");
                if (Directory.Exists(Path.Combine(legacy, "backend"))) return legacy;

                currentDir = currentDir.Parent;
                sanityCheck++;
            }
            return null;
        }

        private string FindBackendSourceRoot(string projectRoot)
        {
            var currentDir = new DirectoryInfo(projectRoot);
            int sanityCheck = 0;
            while (currentDir != null && sanityCheck < 10)
            {
                string candidate = Path.Combine(currentDir.FullName, "src", "backend");
                if (File.Exists(Path.Combine(candidate, "requirements.txt"))) return candidate;
                currentDir = currentDir.Parent;
                sanityCheck++;
            }
            return null;
        }

        // --- Persistence Helpers ---

        private string GetLocalSisRuaDir()
        {
            string localAppData = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
            return Path.Combine(localAppData, "sisRUA");
        }

        private int TryReadLastBackendPort()
        {
            try { return int.Parse(File.ReadAllText(Path.Combine(GetLocalSisRuaDir(), "backend_port.txt"))); }
            catch { return 0; }
        }

        private string TryReadLastBackendToken()
        {
            try { return File.ReadAllText(Path.Combine(GetLocalSisRuaDir(), "backend_token.txt")); }
            catch { return null; }
        }

        private int TryReadLastBackendPid()
        {
            try { return int.Parse(File.ReadAllText(Path.Combine(GetLocalSisRuaDir(), "backend_pid.txt"))); }
            catch { return 0; }
        }

        private void PersistBackendPort(int port) => SafeWrite("backend_port.txt", port.ToString());
        private void PersistBackendToken(string token) => SafeWrite("backend_token.txt", token);
        private void PersistBackendPid(int pid) => SafeWrite("backend_pid.txt", pid.ToString());

        private void SafeWrite(string filename, string content)
        {
            try
            {
                Directory.CreateDirectory(GetLocalSisRuaDir());
                File.WriteAllText(Path.Combine(GetLocalSisRuaDir(), filename), content);
            }
            catch { }
        }

        private int ChooseFreePort()
        {
            var listener = new TcpListener(IPAddress.Loopback, 0);
            try
            {
                listener.Start();
                return ((IPEndPoint)listener.LocalEndpoint).Port;
            }
            finally
            {
                listener.Stop();
            }
        }
    }
}
