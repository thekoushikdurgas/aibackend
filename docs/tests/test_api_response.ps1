$body = @{
    page_data = @{
        url = "https://example.com"
        title = "Example"
        domain = "example.com"
        html = "<html><body>Test</body></html>"
        body_html = ""
        head_html = ""
        meta = @()
        structure = @{}
        images = @()
        videos = @()
        semantic = @{}
        timestamp = "2025-12-18T00:00:00Z"
    }
    query = "Hello"
    options = @{}
} | ConvertTo-Json -Depth 10

$headers = @{
    "Content-Type" = "application/json"
    "X-API-Key" = "ZpKty4B8jLEMQpZiDnFB4ax7ZvdfRyJK"
}

Write-Host "Testing Council API..."
$response = Invoke-WebRequest -Uri "http://localhost:8000/api/v1/council/analyze" -Method POST -Headers $headers -Body $body -TimeoutSec 60

Write-Host "`n=== Response Status ==="
Write-Host "Status Code: $($response.StatusCode)"

Write-Host "`n=== Response Content ==="
$json = $response.Content | ConvertFrom-Json
Write-Host ($json | ConvertTo-Json -Depth 10)
