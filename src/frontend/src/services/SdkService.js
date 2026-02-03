import { SisRuaClient } from '../sdk/client';
import { ResilienceService } from './ResilienceService';

// Determine API base URL (remove /api/v1 suffix if present for SDK)
const API_BASE = import.meta.env.VITE_API_URL || `${window.location.origin}`;
const SDK_BASE = API_BASE.replace(/\/api\/v1$/, '');

// Initialize SDK client singleton
const sdkClient = new SisRuaClient(SDK_BASE);

/**
 * SDK Service Wrapper
 * Integrates the generated TypeScript SDK with frontend resilience patterns.
 * Provides a clean interface for components to interact with backend APIs.
 */
export const SdkService = {
  /**
   * Health Check - Simple
   * @returns {Promise<{status: string}>}
   */
  async checkHealth() {
    return await ResilienceService.executeWithTracing('SDK_HEALTH_CHECK', async () => {
      return await sdkClient.healthApiV1HealthGet();
    });
  },

  /**
   * Health Check - Detailed (includes component status)
   * @returns {Promise<{status: string, components: object, system_latency_ms: number}>}
   */
  async checkHealthDetailed() {
    return await ResilienceService.executeWithTracing('SDK_HEALTH_DETAILED', async () => {
      return await sdkClient.healthDetailedApiV1HealthDetailedGet();
    });
  },

  /**
   * Auth Check
   * @returns {Promise<any>}
   */
  async authCheck() {
    return await ResilienceService.executeWithTracing('SDK_AUTH_CHECK', async () => {
      return await sdkClient.authCheckApiV1AuthCheckGet();
    });
  },

  /**
   * Update Project Settings
   * @param {string} projectId - Project ID
   * @param {object} data - Project update data (version, project_name, crs_out)
   * @returns {Promise<any>}
   */
  async updateProject(projectId, data) {
    return await ResilienceService.executeWithTracing('SDK_UPDATE_PROJECT', async () => {
      // Note: SDK has path parameter {project_id} - would need to fix SDK generation
      // For now, using as-is (will need backend fix)
      return await sdkClient.updateProjectApiV1ProjectsProjectIdPut(data);
    });
  },

  /**
   * Create Prepare Job (OSM or GeoJSON)
   * @param {object} jobRequest - PrepareJobRequest (kind, latitude, longitude, radius, geojson)
   * @returns {Promise<any>}
   */
  async createPrepareJob(jobRequest) {
    return await ResilienceService.executeWithTracing('SDK_CREATE_JOB', async () => {
      return await sdkClient.createPrepareJobApiV1JobsPreparePost(jobRequest);
    });
  },

  /**
   * Get Job Status
   * @param {string} jobId - Job ID
   * @returns {Promise<JobStatusResponse>}
   */
  async getJob(_jobId) {
    return await ResilienceService.executeWithTracing('SDK_GET_JOB', async () => {
      // Note: SDK has path parameter {job_id} - would need to fix SDK generation
      // TODO: Pass jobId to SDK once path parameters are properly implemented
      return await sdkClient.getJobEndpointApiV1JobsJobIdGet();
    });
  },

  /**
   * Cancel Job
   * @param {string} jobId - Job ID
   * @returns {Promise<any>}
   */
  async cancelJob(_jobId) {
    return await ResilienceService.executeWithTracing('SDK_CANCEL_JOB', async () => {
      // TODO: Pass jobId to SDK once path parameters are properly implemented
      return await sdkClient.cancelJobEndpointApiV1JobsJobIdDelete();
    });
  },

  /**
   * Query Elevation for a Point
   * @param {number} latitude
   * @param {number} longitude
   * @returns {Promise<ElevationPointResponse>}
   */
  async queryElevation(latitude, longitude) {
    return await ResilienceService.executeWithTracing('SDK_ELEVATION_QUERY', async () => {
      return await sdkClient.queryElevationApiV1ToolsElevationQueryPost({ latitude, longitude });
    });
  },

  /**
   * Query Elevation Profile for a Path
   * @param {Array<[number, number]>} path - Array of [lat, lng] coordinates
   * @returns {Promise<ElevationProfileResponse>}
   */
  async queryElevationProfile(path) {
    return await ResilienceService.executeWithTracing('SDK_ELEVATION_PROFILE', async () => {
      return await sdkClient.queryProfileApiV1ToolsElevationProfilePost({ path });
    });
  },

  /**
   * Chat with AI Assistant
   * @param {string} message - User message
   * @param {object} context - Optional context
   * @param {string} jobId - Optional job ID
   * @returns {Promise<ChatResponse>}
   */
  async chatWithAI(message, context = null, jobId = null) {
    return await ResilienceService.executeWithTracing('SDK_AI_CHAT', async () => {
      return await sdkClient.chatWithAiApiV1AiChatPost({ message, context, job_id: jobId });
    });
  },

  /**
   * Prepare OSM Data - Orchestrated via AutoCAD Host
   * @param {number} latitude
   * @param {number} longitude
   * @param {number} radius
   */
  async prepareOSM(latitude, longitude, radius) {
    if (window.chrome?.webview) {
      // IPC Orchestration: Delegate to C# Host
      window.chrome.webview.postMessage({
        action: 'GENERATE_OSM',
        data: { latitude, longitude, radius }
      });
      return { status: 'orchestrated' };
    }

    // Fallback for development/web
    return await ResilienceService.executeWithTracing('SDK_PREPARE_OSM', async () => {
      return await ResilienceService.guard('OSM_API', async () => {
        return await sdkClient.prepareOsmApiV1PrepareOsmPost({ latitude, longitude, radius });
      });
    });
  },

  /**
   * Prepare GeoJSON Data - Orchestrated via AutoCAD Host
   * @param {object} geojson - GeoJSON object
   */
  async prepareGeoJSON(geojson) {
    if (window.chrome?.webview) {
      // IPC Orchestration: Delegate to C# Host
      window.chrome.webview.postMessage({
        action: 'IMPORT_GEOJSON',
        data: geojson
      });
      return { status: 'orchestrated' };
    }

    // Fallback for development/web
    return await ResilienceService.executeWithTracing('SDK_PREPARE_GEOJSON', async () => {
      return await sdkClient.prepareGeojsonApiV1PrepareGeojsonPost({ geojson });
    });
  },

  /**
   * Register Webhook
   * @param {string} url - Webhook URL
   * @param {Array<string>} events - Event types to subscribe to
   * @returns {Promise<any>}
   */
  async registerWebhook(url, events = null) {
    return await ResilienceService.executeWithTracing('SDK_WEBHOOK_REGISTER', async () => {
      return await sdkClient.registerWebhookApiV1WebhooksRegisterPost({ url, events });
    });
  },

  /**
   * Emit Internal Event
   * @param {string} eventType - Event type
   * @param {object} payload - Event payload
   * @returns {Promise<any>}
   */
  async emitEvent(eventType, payload) {
    return await ResilienceService.executeWithTracing('SDK_EMIT_EVENT', async () => {
      return await sdkClient.emitEventApiV1EventsEmitPost({ event_type: eventType, payload });
    });
  },

  /**
   * Create Audit Log
   * @param {object} auditData - Audit log data
   * @returns {Promise<any>}
   */
  async createAuditLog(auditData) {
    return await ResilienceService.executeWithTracing('SDK_AUDIT_CREATE', async () => {
      return await sdkClient.createAuditLogApiAuditPost(auditData);
    });
  },

  /**
   * List Audit Logs
   * @returns {Promise<any>}
   */
  async listAuditLogs() {
    return await ResilienceService.executeWithTracing('SDK_AUDIT_LIST', async () => {
      return await sdkClient.listAuditLogsApiAuditGet();
    });
  },

  /**
   * Get Audit Log by ID
   * @param {string} auditId - Audit log ID
   * @returns {Promise<any>}
   */
  async getAuditLog(_auditId) {
    return await ResilienceService.executeWithTracing('SDK_AUDIT_GET', async () => {
      // TODO: Pass auditId to SDK once path parameters are properly implemented
      return await sdkClient.getAuditLogApiAuditAuditIdGet();
    });
  },

  /**
   * Verify Audit Log
   * @param {string} auditId - Audit log ID
   * @returns {Promise<any>}
   */
  async verifyAuditLog(_auditId) {
    return await ResilienceService.executeWithTracing('SDK_AUDIT_VERIFY', async () => {
      // TODO: Pass auditId to SDK once path parameters are properly implemented
      return await sdkClient.verifyAuditLogApiAuditAuditIdVerifyGet();
    });
  },

  /**
   * Verify All Audit Logs
   * @param {object} options - Verification options
   * @returns {Promise<any>}
   */
  async verifyAllAuditLogs(options = {}) {
    return await ResilienceService.executeWithTracing('SDK_AUDIT_VERIFY_ALL', async () => {
      return await sdkClient.verifyAllLogsApiAuditVerifyAllPost(options);
    });
  },

  /**
   * Get Audit Statistics
   * @returns {Promise<any>}
   */
  async getAuditStats() {
    return await ResilienceService.executeWithTracing('SDK_AUDIT_STATS', async () => {
      return await sdkClient.getAuditStatsApiAuditStatsGet();
    });
  },
};
