resource "google_cloud_run_v2_service" "sisrua" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      max_instance_count = 50
      min_instance_count = 2
    }

    service_account = google_service_account.sisrua_sa.email

    containers {
      image = var.container_image

      resources {
        limits = {
          cpu    = "1"
          memory = "1Gi"
        }
      }

      env {
        name  = "ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "SENTRY_ENVIRONMENT"
        value = "production"
      }

      env {
        name  = "SENTRY_RELEASE"
        value = "sisrua-backend@${var.image_tag}"
      }

      # CORS_ORIGINS: comma-separated list of allowed origins for the Cloud Run instance.
      # The backend reads this via SISRUA_CORS_ORIGINS env var.
      env {
        name  = "SISRUA_CORS_ORIGINS"
        value = var.cors_origins
      }
    }
  }

  # Blue/Green Traffic Management
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }
}

# Allow unauthenticated access (Public API)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.sisrua.name
  location = google_cloud_run_v2_service.sisrua.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
