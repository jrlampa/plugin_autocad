output "service_url" {
  description = "The URL of the deployed Cloud Run service"
  value       = google_cloud_run_v2_service.sisrua.uri
}

output "service_account_email" {
  description = "The email of the production service account"
  value       = google_service_account.sisrua_sa.email
}
