param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$requestBody = @{
    floor_limits = @{
        max_width = 120.0
        max_height = 100.0
    }
    aspect_ratio = "4:3"
    rooms = @(
        @{ id = "bedroom_1"; room_type = "bedroom"; requested_size = "regular" }
        @{ id = "bathroom_1"; room_type = "bathroom"; requested_size = "regular" }
        @{ id = "kitchen_1"; room_type = "kitchen"; requested_size = "regular" }
        @{ id = "veranda_1"; room_type = "veranda"; requested_size = "regular" }
    )
} | ConvertTo-Json -Depth 10

Write-Host "Calling $BaseUrl/generation (the solver can take about 30 seconds)..."
$response = Invoke-RestMethod `
    -Method Post `
    -Uri "$BaseUrl/generation" `
    -ContentType "application/json" `
    -Body $requestBody

if ($null -eq $response.floor_plan -or $null -eq $response.scoring) {
    throw "Generation API returned an unexpected response shape."
}

$roomCount = @($response.floor_plan.rooms).Count
$openingCount = @($response.floor_plan.openings).Count
Write-Host "Generation API is working." -ForegroundColor Green
Write-Host "Rooms: $roomCount | Openings: $openingCount | Score: $($response.scoring.total_score)"
$response | ConvertTo-Json -Depth 20
