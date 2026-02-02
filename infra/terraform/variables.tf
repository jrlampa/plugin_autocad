variable "project_id" {
  description = "The GCP project ID"
  type        = string
}

variable "region" {
  description = "The GCP region to deploy to"
  type        = string
  default     = "us-central1"
}

variable "service_name" {
  description = "The name of the Cloud Run service"
  type        = string
  default     = "sisrua-backend"
}

variable "image_tag" {
  description = "The container image tag for v0.9.0"
  type        = string
  default     = "v0.9.0"
}

variable "container_image" {
  description = "The full URI of the container image"
  type        = string
}
