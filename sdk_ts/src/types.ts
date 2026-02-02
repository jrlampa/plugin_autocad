// Generated TypeScript Interfaces

export interface CadFeature {
  feature_type?: string;
  layer?: any;
  name?: any;
  highway?: any;
  width_m?: any;
  coords_xy?: any;
  insertion_point_xy?: any;
  block_name?: any;
  block_filepath?: any;
  rotation?: any;
  scale?: any;
  color?: any;
  elevation?: any;
  slope?: any;
}

export interface ChatRequest {
  message: string;
  context?: any;
  job_id?: any;
}

export interface ChatResponse {
  response: string;
}

export interface ComponentHealth {
  status: string;
  details?: any;
  latency_ms?: any;
}

export interface DeepHealthResponse {
  status: string;
  components: any;
  system_latency_ms: number;
}

export interface ElevationPointResponse {
  latitude: number;
  longitude: number;
  elevation?: any;
}

export interface ElevationProfileRequest {
  path: any[];
}

export interface ElevationProfileResponse {
  elevations: any[];
}

export interface ElevationQueryRequest {
  latitude: number;
  longitude: number;
}

export interface HTTPValidationError {
  detail?: any[];
}

export interface HealthResponse {
  status: string;
}

export interface InternalEvent {
  event_type: string;
  payload: any;
}

export interface JobStatusResponse {
  job_id: string;
  kind: string;
  status: string;
  progress: number;
  message?: any;
  result?: any;
  error?: any;
  created_at: number;
  updated_at: number;
}

export interface PrepareGeoJsonRequest {
  geojson: any;
}

export interface PrepareJobRequest {
  kind: string;
  latitude?: any;
  longitude?: any;
  radius?: any;
  geojson?: any;
}

export interface PrepareOsmRequest {
  latitude: number;
  longitude: number;
  radius: number;
}

export interface PrepareResponse {
  crs_out?: any;
  features: any[];
  cache_hit?: any;
}

export interface ProjectUpdateRequest {
  version: number;
  project_name?: any;
  crs_out?: any;
}

export interface ValidationError {
  loc: any[];
  msg: string;
  type: string;
}

export interface WebhookRegistrationRequest {
  url: string;
  events?: any;
}

