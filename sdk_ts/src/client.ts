import { CadFeature, ChatRequest, ChatResponse, ComponentHealth, DeepHealthResponse, ElevationPointResponse, ElevationProfileRequest, ElevationProfileResponse, ElevationQueryRequest, HTTPValidationError, HealthResponse, InternalEvent, JobStatusResponse, PrepareGeoJsonRequest, PrepareJobRequest, PrepareOsmRequest, PrepareResponse, ProjectUpdateRequest, ValidationError, WebhookRegistrationRequest } from './types';

export class SisRuaClient {
  private baseUrl: string;
  private token?: string;

  constructor(baseUrl: string, token?: string) {
    this.baseUrl = baseUrl.replace(/\/$/, '');
    this.token = token;
  }

  private async request<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: HeadersInit = { 'Content-Type': 'application/json' };
    if (this.token) headers['X-SisRua-Token'] = this.token;
    const response = await fetch(`${this.baseUrl}${path}`, { ...options, headers });
    if (!response.ok) throw new Error(`API Error: ${response.statusText}`);
    return response.json();
  }

  async authCheckApiV1AuthCheckGet(): Promise<any> {
    return this.request('/api/v1/auth/check', { method: 'GET' });
  }

  async healthApiV1HealthGet(): Promise<any> {
    return this.request('/api/v1/health', { method: 'GET' });
  }

  async healthDetailedApiV1HealthDetailedGet(): Promise<any> {
    return this.request('/api/v1/health/detailed', { method: 'GET' });
  }

  async updateProjectApiV1ProjectsProjectIdPut(body: any): Promise<any> {
    return this.request('/api/v1/projects/{project_id}', { method: 'PUT', body: JSON.stringify(body) });
  }

  async createPrepareJobApiV1JobsPreparePost(body: any): Promise<any> {
    return this.request('/api/v1/jobs/prepare', { method: 'POST', body: JSON.stringify(body) });
  }

  async getJobEndpointApiV1JobsJobIdGet(): Promise<any> {
    return this.request('/api/v1/jobs/{job_id}', { method: 'GET' });
  }

  async cancelJobEndpointApiV1JobsJobIdDelete(): Promise<any> {
    return this.request('/api/v1/jobs/{job_id}', { method: 'DELETE' });
  }

  async queryElevationApiV1ToolsElevationQueryPost(body: any): Promise<any> {
    return this.request('/api/v1/tools/elevation/query', { method: 'POST', body: JSON.stringify(body) });
  }

  async queryProfileApiV1ToolsElevationProfilePost(body: any): Promise<any> {
    return this.request('/api/v1/tools/elevation/profile', { method: 'POST', body: JSON.stringify(body) });
  }

  async chatWithAiApiV1AiChatPost(body: any): Promise<any> {
    return this.request('/api/v1/ai/chat', { method: 'POST', body: JSON.stringify(body) });
  }

  async prepareOsmApiV1PrepareOsmPost(body: any): Promise<any> {
    return this.request('/api/v1/prepare/osm', { method: 'POST', body: JSON.stringify(body) });
  }

  async prepareGeojsonApiV1PrepareGeojsonPost(body: any): Promise<any> {
    return this.request('/api/v1/prepare/geojson', { method: 'POST', body: JSON.stringify(body) });
  }

  async registerWebhookApiV1WebhooksRegisterPost(body: any): Promise<any> {
    return this.request('/api/v1/webhooks/register', { method: 'POST', body: JSON.stringify(body) });
  }

  async emitEventApiV1EventsEmitPost(body: any): Promise<any> {
    return this.request('/api/v1/events/emit', { method: 'POST', body: JSON.stringify(body) });
  }

  async createAuditLogApiAuditPost(body: any): Promise<any> {
    return this.request('/api/audit', { method: 'POST', body: JSON.stringify(body) });
  }

  async listAuditLogsApiAuditGet(): Promise<any> {
    return this.request('/api/audit', { method: 'GET' });
  }

  async getAuditLogApiAuditAuditIdGet(): Promise<any> {
    return this.request('/api/audit/{audit_id}', { method: 'GET' });
  }

  async verifyAuditLogApiAuditAuditIdVerifyGet(): Promise<any> {
    return this.request('/api/audit/{audit_id}/verify', { method: 'GET' });
  }

  async verifyAllLogsApiAuditVerifyAllPost(body: any): Promise<any> {
    return this.request('/api/audit/verify-all', { method: 'POST', body: JSON.stringify(body) });
  }

  async getAuditStatsApiAuditStatsGet(): Promise<any> {
    return this.request('/api/audit/stats', { method: 'GET' });
  }

  async rootGet(): Promise<any> {
    return this.request('/', { method: 'GET' });
  }

}
