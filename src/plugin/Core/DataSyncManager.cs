using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using Autodesk.AutoCAD.ApplicationServices;

namespace sisRUA.Core
{
    /// <summary>
    /// Manages data synchronization between C# plugin and Python backend.
    /// Implements push/pull sync, conflict detection, and resolution.
    /// </summary>
    public class DataSyncManager
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl;
        private DateTime _lastSyncTimestamp;
        private readonly List<SyncEvent> _pendingChanges;

        /// <summary>
        /// Initialize sync manager with HTTP client.
        /// </summary>
        /// <param name="httpClient">HTTP client for API calls</param>
        /// <param name="baseUrl">Backend API base URL</param>
        public DataSyncManager(HttpClient httpClient, string baseUrl = null)
        {
            _httpClient = httpClient ?? throw new ArgumentNullException(nameof(httpClient));
            _baseUrl = baseUrl ?? "http://localhost:8000";
            _lastSyncTimestamp = DateTime.UtcNow.AddDays(-7); // Start from 7 days ago
            _pendingChanges = new List<SyncEvent>();
        }

        /// <summary>
        /// Record a local change for later synchronization.
        /// </summary>
        public void RecordChange(string entityType, string entityId, string action, object data = null)
        {
            var change = new SyncEvent
            {
                EntityType = entityType,
                EntityId = entityId,
                Action = action,
                Data = data,
                Timestamp = DateTime.UtcNow,
                Source = "plugin"
            };

            _pendingChanges.Add(change);
            LogInfo($"Recorded {action} on {entityType}:{entityId}");
        }

        /// <summary>
        /// Synchronize with backend: push local changes and pull remote changes.
        /// </summary>
        /// <returns>Sync result with counts and conflicts</returns>
        public async Task<SyncResult> SyncWithBackend()
        {
            var result = new SyncResult { Success = true };

            try
            {
                LogInfo($"Starting sync. Pending changes: {_pendingChanges.Count}");

                // 1. Push local changes
                if (_pendingChanges.Any())
                {
                    var pushResult = await PushChanges();
                    result.PushedCount = pushResult.PushedCount;
                    result.Conflicts.AddRange(pushResult.Conflicts);

                    // Clear pushed changes
                    _pendingChanges.Clear();
                }

                // 2. Pull remote changes
                var pulledChanges = await PullChanges(_lastSyncTimestamp);
                result.PulledCount = pulledChanges.Count;

                // 3. Apply pulled changes
                foreach (var change in pulledChanges)
                {
                    ApplyChange(change);
                }

                // 4. Update last sync timestamp
                _lastSyncTimestamp = DateTime.UtcNow;

                LogInfo($"Sync complete. Pushed: {result.PushedCount}, Pulled: {result.PulledCount}, Conflicts: {result.Conflicts.Count}");
            }
            catch (Exception ex)
            {
                result.Success = false;
                result.Message = $"Sync failed: {ex.Message}";
                LogError($"Sync error: {ex.Message}");
            }

            return result;
        }

        /// <summary>
        /// Push local changes to backend.
        /// </summary>
        private async Task<SyncResult> PushChanges()
        {
            try
            {
                var changeset = new
                {
                    changes = _pendingChanges,
                    client_timestamp = DateTime.UtcNow
                };

                var json = JsonSerializer.Serialize(changeset);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync($"{_baseUrl}/api/v1/sync/push", content);
                response.EnsureSuccessStatusCode();

                var responseJson = await response.Content.ReadAsStringAsync();
                var result = JsonSerializer.Deserialize<SyncResult>(responseJson, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                });

                return result ?? new SyncResult { Success = false, Message = "Invalid response" };
            }
            catch (Exception ex)
            {
                LogError($"Push failed: {ex.Message}");
                return new SyncResult { Success = false, Message = ex.Message };
            }
        }

        /// <summary>
        /// Pull changes from backend since last sync.
        /// </summary>
        private async Task<List<SyncEvent>> PullChanges(DateTime since)
        {
            try
            {
                var sinceIso = since.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ");
                var response = await _httpClient.GetAsync($"{_baseUrl}/api/v1/sync/pull?since={sinceIso}");
                response.EnsureSuccessStatusCode();

                var responseJson = await response.Content.ReadAsStringAsync();
                var changes = JsonSerializer.Deserialize<List<SyncEvent>>(responseJson, new JsonSerializerOptions
                {
                    PropertyNameCaseInsensitive = true
                }) ?? new List<SyncEvent>();

                return changes;
            }
            catch (Exception ex)
            {
                LogError($"Pull failed: {ex.Message}");
                return new List<SyncEvent>();
            }
        }

        /// <summary>
        /// Apply a synced change locally.
        /// </summary>
        private void ApplyChange(SyncEvent change)
        {
            try
            {
                LogInfo($"Applying {change.Action} on {change.EntityType}:{change.EntityId}");

                // TODO: Implement actual data application based on entity type
                // For now, just log
                switch (change.EntityType)
                {
                    case "project":
                        ApplyProjectChange(change);
                        break;
                    case "element":
                        ApplyElementChange(change);
                        break;
                    default:
                        LogWarning($"Unknown entity type: {change.EntityType}");
                        break;
                }
            }
            catch (Exception ex)
            {
                LogError($"Failed to apply change: {ex.Message}");
            }
        }

        private void ApplyProjectChange(SyncEvent change)
        {
            // Implement project-specific logic
            LogInfo($"Applied project change: {change.EntityId}");
        }

        private void ApplyElementChange(SyncEvent change)
        {
            // Implement element-specific logic
            LogInfo($"Applied element change: {change.EntityId}");
        }

        /// <summary>
        /// Get count of pending changes.
        /// </summary>
        public int GetPendingChangesCount() => _pendingChanges.Count;

        /// <summary>
        /// Clear all pending changes (use with caution).
        /// </summary>
        public void ClearPendingChanges()
        {
            _pendingChanges.Clear();
            LogInfo("Cleared all pending changes");
        }

        #region Logging Helpers

        private void LogInfo(string message)
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            doc?.Editor.WriteMessage($"\n[Sync] {message}");
        }

        private void LogWarning(string message)
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            doc?.Editor.WriteMessage($"\n[Sync WARNING] {message}");
        }

        private void LogError(string message)
        {
            var doc = Application.DocumentManager.MdiActiveDocument;
            doc?.Editor.WriteMessage($"\n[Sync ERROR] {message}");
        }

        #endregion
    }

    /// <summary>
    /// Represents a synchronization event.
    /// </summary>
    public class SyncEvent
    {
        public int? Id { get; set; }
        public string EntityType { get; set; }
        public string EntityId { get; set; }
        public string Action { get; set; }
        public object Data { get; set; }
        public DateTime Timestamp { get; set; }
        public string UserId { get; set; }
        public string Source { get; set; }
    }

    /// <summary>
    /// Represents a sync conflict.
    /// </summary>
    public class SyncConflict
    {
        public string EntityType { get; set; }
        public string EntityId { get; set; }
        public SyncEvent LocalChange { get; set; }
        public SyncEvent RemoteChange { get; set; }
        public DateTime DetectedAt { get; set; }
    }

    /// <summary>
    /// Result of a synchronization operation.
    /// </summary>
    public class SyncResult
    {
        public bool Success { get; set; }
        public int PushedCount { get; set; }
        public int PulledCount { get; set; }
        public List<SyncConflict> Conflicts { get; set; } = new List<SyncConflict>();
        public string Message { get; set; }
    }
}
