import httpx
from typing import Optional, Dict, Any
from .models import *

class SisRuaClient:
    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip('/')
        self.headers = {'X-SisRua-Token': token} if token else {}
        self.client = httpx.Client(base_url=self.base_url, headers=self.headers)

    def auth_check_api_v1_auth_check_get(self) -> Any:
        '''Auth Check'''
        resp = self.client.get('/api/v1/auth/check')
        resp.raise_for_status()
        return resp.json()

    def health_api_v1_health_get(self) -> Any:
        '''Health'''
        resp = self.client.get('/api/v1/health')
        resp.raise_for_status()
        return resp.json()

    def health_detailed_api_v1_health_detailed_get(self) -> Any:
        '''Health Detailed'''
        resp = self.client.get('/api/v1/health/detailed')
        resp.raise_for_status()
        return resp.json()

    def update_project_api_v1_projects__project_id__put(self, body: Dict[str, Any]) -> Any:
        '''Update Project'''
        resp = self.client.put('/api/v1/projects/{project_id}', json=body)
        resp.raise_for_status()
        return resp.json()

    def create_prepare_job_api_v1_jobs_prepare_post(self, body: Dict[str, Any]) -> Any:
        '''Create Prepare Job'''
        resp = self.client.post('/api/v1/jobs/prepare', json=body)
        resp.raise_for_status()
        return resp.json()

    def get_job_endpoint_api_v1_jobs__job_id__get(self) -> Any:
        '''Get Job Endpoint'''
        resp = self.client.get('/api/v1/jobs/{job_id}')
        resp.raise_for_status()
        return resp.json()

    def cancel_job_endpoint_api_v1_jobs__job_id__delete(self) -> Any:
        '''Cancel Job Endpoint'''
        resp = self.client.delete('/api/v1/jobs/{job_id}')
        resp.raise_for_status()
        return resp.json()

    def query_elevation_api_v1_tools_elevation_query_post(self, body: Dict[str, Any]) -> Any:
        '''Query Elevation'''
        resp = self.client.post('/api/v1/tools/elevation/query', json=body)
        resp.raise_for_status()
        return resp.json()

    def query_profile_api_v1_tools_elevation_profile_post(self, body: Dict[str, Any]) -> Any:
        '''Query Profile'''
        resp = self.client.post('/api/v1/tools/elevation/profile', json=body)
        resp.raise_for_status()
        return resp.json()

    def chat_with_ai_api_v1_ai_chat_post(self, body: Dict[str, Any]) -> Any:
        '''Chat With Ai'''
        resp = self.client.post('/api/v1/ai/chat', json=body)
        resp.raise_for_status()
        return resp.json()

    def prepare_osm_api_v1_prepare_osm_post(self, body: Dict[str, Any]) -> Any:
        '''Prepare Osm'''
        resp = self.client.post('/api/v1/prepare/osm', json=body)
        resp.raise_for_status()
        return resp.json()

    def prepare_geojson_api_v1_prepare_geojson_post(self, body: Dict[str, Any]) -> Any:
        '''Prepare Geojson'''
        resp = self.client.post('/api/v1/prepare/geojson', json=body)
        resp.raise_for_status()
        return resp.json()

    def register_webhook_api_v1_webhooks_register_post(self, body: Dict[str, Any]) -> Any:
        '''Register Webhook'''
        resp = self.client.post('/api/v1/webhooks/register', json=body)
        resp.raise_for_status()
        return resp.json()

    def emit_event_api_v1_events_emit_post(self, body: Dict[str, Any]) -> Any:
        '''Emit Event'''
        resp = self.client.post('/api/v1/events/emit', json=body)
        resp.raise_for_status()
        return resp.json()

    def create_audit_log_api_audit_post(self, body: Dict[str, Any]) -> Any:
        '''Create Audit Log'''
        resp = self.client.post('/api/audit', json=body)
        resp.raise_for_status()
        return resp.json()

    def list_audit_logs_api_audit_get(self) -> Any:
        '''List Audit Logs'''
        resp = self.client.get('/api/audit')
        resp.raise_for_status()
        return resp.json()

    def get_audit_log_api_audit__audit_id__get(self) -> Any:
        '''Get Audit Log'''
        resp = self.client.get('/api/audit/{audit_id}')
        resp.raise_for_status()
        return resp.json()

    def verify_audit_log_api_audit__audit_id__verify_get(self) -> Any:
        '''Verify Audit Log'''
        resp = self.client.get('/api/audit/{audit_id}/verify')
        resp.raise_for_status()
        return resp.json()

    def verify_all_logs_api_audit_verify_all_post(self, body: Dict[str, Any]) -> Any:
        '''Verify All Logs'''
        resp = self.client.post('/api/audit/verify-all', json=body)
        resp.raise_for_status()
        return resp.json()

    def get_audit_stats_api_audit_stats_get(self) -> Any:
        '''Get Audit Stats'''
        resp = self.client.get('/api/audit/stats')
        resp.raise_for_status()
        return resp.json()

    def root__get(self) -> Any:
        '''Root'''
        resp = self.client.get('/')
        resp.raise_for_status()
        return resp.json()

