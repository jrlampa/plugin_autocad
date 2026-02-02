resource "google_cloud_run_v2_service" "sisrua" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      max_instance_count = 10
      min_instance_count = 1
    }

    containers {
      image = var.container_image
      
      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "SENTRY_ENVIRONMENT"
        value = "production"
      }
      
      env {
        name  = "SENTRY_RELEASE"
        value = "sisrua-backend@${var.image_tag}"
      }
    }
  }
}

# Allow unauthenticated access (Public API)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.sisrua.name
  location = google_cloud_run_v2_service.sisrua.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
