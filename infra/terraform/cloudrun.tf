resource "google_cloud_run_v2_service" "sisrua" {
  name     = var.service_name
  location = var.region
  ingress  = "INGRESS_TRAFFIC_ALL"

  template {
    scaling {
      max_instance_count = 50   # Increased for 10k users baseline
      min_instance_count = 2    # Prevent cold starts under load
    }
    
    # High concurrency settings
    revision_name = "sisrua-backend-v090-concurrency-locked"

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

  # Blue/Green Traffic Management
  traffic {
    type    = "TRAFFIC_TARGET_ALLOCATION_TYPE_LATEST"
    percent = 100
  }

  # Optional: Keep previous revision for fast rollback
  # This is usually managed via CLI during deploy, 
  # but we can preserve the structure here.
}

# Allow unauthenticated access (Public API)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  name     = google_cloud_run_v2_service.sisrua.name
  location = google_cloud_run_v2_service.sisrua.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}
