<#
.SYNOPSIS
    Runs locust load test locally against the backend.
#>
param(
  [string]$TargetUrl = "http://localhost:5050",
  [int]$Users = 100,
  [int]$SpawnRate = 10,
  [string]$RunTime = "1m"
)

Write-Host "--- Starting Load Test Simulation ---" -ForegroundColor Cyan
Write-Host "Target: $TargetUrl"
Write-Host "Users: $Users"

# Ensure locust is installed
if (-not (Get-Command locust -ErrorAction SilentlyContinue)) {
  Write-Host "Locust not found. Installing..."
  pip install locust
}

# Run locust in headless mode
locust -f tests/locustfile.py --headless -u $Users -r $SpawnRate --run-time $RunTime --host $TargetUrl --csv=tests/load_test_results

Write-Host "Load test complete. Results saved to tests/load_test_results_stats.csv" -ForegroundColor Green
