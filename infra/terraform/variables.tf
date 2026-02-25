variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy to"
  type        = string
  default     = "southamerica-east1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "sisrua-backend"
}

variable "image_tag" {
  description = "The container image tag to deploy (e.g. v0.2.0-alpha)"
  type        = string
  default     = "latest"
}

variable "container_image" {
  description = "The full URI of the container image (e.g. gcr.io/PROJECT/sisrua-backend:TAG)"
  type        = string
}

variable "cors_origins" {
  description = "Comma-separated list of allowed CORS origins for the backend (e.g. https://sisrua.app)"
  type        = string
  default     = ""
}
