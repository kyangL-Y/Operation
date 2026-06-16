$ErrorActionPreference = "Stop"

$baseUrl = "http://localhost:8080"

function Assert-Field($obj, $field, $msg) {
  if ($null -eq $obj.$field) {
    throw $msg
  }
}

function Assert-DataField($resp, $field, $msg) {
  Assert-Field $resp "data" "response missing data"
  if ($null -eq $resp.data.$field) {
    throw $msg
  }
}

function Invoke-JsonApi {
  param(
    [Parameter(Mandatory = $true)][ValidateSet("GET", "POST")][string]$Method,
    [Parameter(Mandatory = $true)][string]$Uri,
    [hashtable]$Headers,
    [object]$BodyObject,
    [int]$TimeoutSec = 12,
    [int]$Retry = 2,
    [int]$RetryDelaySec = 2
  )

  $lastError = $null
  for ($i = 0; $i -le $Retry; $i++) {
    try {
      if ($Method -eq "GET") {
        return Invoke-RestMethod -Method Get -Uri $Uri -Headers $Headers -TimeoutSec $TimeoutSec
      }

      $jsonBody = $null
      if ($null -ne $BodyObject) {
        $jsonBody = $BodyObject | ConvertTo-Json -Depth 8 -Compress
      }
      return Invoke-RestMethod -Method Post -Uri $Uri -Headers $Headers -ContentType "application/json; charset=utf-8" -Body $jsonBody -TimeoutSec $TimeoutSec
    } catch {
      $lastError = $_
      if ($i -lt $Retry) {
        Start-Sleep -Seconds $RetryDelaySec
      }
    }
  }

  if ($null -ne $lastError) {
    throw $lastError
  }
  throw "API request failed: $Method $Uri"
}

$forecastFeatures = @{
  day_of_week = 5
  month = 3
  is_weekend = 1
  is_holiday = 0
  weather_score = 4
  nearby_event = 1
  occ_lag1 = 0.83
  occ_lag7 = 0.74
  occ_roll7 = 0.79
  rev_lag1 = 131000
  rev_lag7 = 102000
  rev_roll7 = 117714.29
  review_score = 4.5
  negative_rate = 0.06
}

Write-Host "[1/9] Login..."
$login = Invoke-JsonApi -Method "POST" -Uri "$baseUrl/api/auth/login" -BodyObject @{
  username = "admin"
  password = "admin123"
}
Assert-Field $login "data" "login response missing data"
$token = $login.data.token
if ([string]::IsNullOrWhiteSpace($token)) { throw "login token is empty" }

$headers = @{ "X-Auth-Token" = $token }

Write-Host "[2/9] ML status..."
$mlStatus = Invoke-JsonApi -Method "GET" -Uri "$baseUrl/api/ml/status" -Headers $headers
Assert-DataField $mlStatus "ml_service" "ml status missing ml_service"
if ($mlStatus.data.ml_service -ne "running") {
  throw "ml service is not running"
}
Assert-DataField $mlStatus "retrievalMode" "ml status missing retrievalMode"
Assert-DataField $mlStatus "generationMode" "ml status missing generationMode"

Write-Host "[3/9] Ask..."
$ask = Invoke-JsonApi -Method "POST" -Uri "$baseUrl/api/rag/ask" -Headers $headers -BodyObject @{
  question = "How to handle a room odor complaint?"
} -TimeoutSec 20 -Retry 3 -RetryDelaySec 3
Assert-Field $ask "code" "ask response missing code"
if ($ask.code -ne 0) {
  $askMessage = if ($ask.message) { $ask.message } else { "unknown ask error" }
  throw "ask failed: $askMessage"
}
Assert-DataField $ask "answer" "ask response missing answer"
Assert-DataField $ask "retrievalMode" "ask response missing retrievalMode"
Assert-DataField $ask "generationMode" "ask response missing generationMode"
Assert-DataField $ask "source" "ask response missing source"
if ($ask.data.retrievalMode -eq "unknown") {
  throw "ask retrievalMode is unknown"
}
if ($ask.data.generationMode -eq "unknown") {
  throw "ask generationMode is unknown"
}

Write-Host "[4/9] Deep search..."
$deepSearch = Invoke-JsonApi -Method "POST" -Uri "$baseUrl/api/rag/deep-search" -Headers $headers -BodyObject @{
  question = "How to handle a room odor complaint?"
} -TimeoutSec 20 -Retry 3 -RetryDelaySec 3
Assert-Field $deepSearch "code" "deep search response missing code"
if ($deepSearch.code -ne 0) {
  $deepSearchMessage = if ($deepSearch.message) { $deepSearch.message } else { "unknown deep search error" }
  throw "deep search failed: $deepSearchMessage"
}
Assert-DataField $deepSearch "answer" "deep search response missing answer"
Assert-DataField $deepSearch "queryPlan" "deep search response missing queryPlan"
Assert-DataField $deepSearch "mode" "deep search response missing mode"
Assert-DataField $deepSearch "retrievalMode" "deep search response missing retrievalMode"
Assert-DataField $deepSearch "generationMode" "deep search response missing generationMode"
Assert-DataField $deepSearch "source" "deep search response missing source"
if ($deepSearch.data.mode -ne "deep-search") {
  throw "deep search mode mismatch"
}
if ($deepSearch.data.retrievalMode -eq "unknown") {
  throw "deep search retrievalMode is unknown"
}
if ($deepSearch.data.generationMode -eq "unknown") {
  throw "deep search generationMode is unknown"
}

Write-Host "[5/9] Dashboard..."
$dash = Invoke-JsonApi -Method "GET" -Uri "$baseUrl/api/ops/dashboard" -Headers $headers
Assert-DataField $dash "occupancyRate" "dashboard response missing occupancyRate"
Assert-DataField $dash "dailyRevenue" "dashboard response missing dailyRevenue"

Write-Host "[6/9] Decision support..."
$decision = Invoke-JsonApi -Method "GET" -Uri "$baseUrl/api/ops/decision-support" -Headers $headers -TimeoutSec 20 -Retry 2 -RetryDelaySec 2
Assert-DataField $decision "forecast" "decision support response missing forecast"
Assert-DataField $decision "decision" "decision support response missing decision"
Assert-DataField $decision "knowledgeAdvice" "decision support response missing knowledgeAdvice"

Write-Host "[7/9] Predict occupancy..."
$occBody = @{ features = $forecastFeatures }
$occ = Invoke-JsonApi -Method "POST" -Uri "$baseUrl/api/ml/predict-occupancy" -Headers $headers -BodyObject $occBody
Assert-DataField $occ "predicted_occupancy" "occupancy prediction missing predicted_occupancy"

Write-Host "[8/9] Predict revenue..."
$rev = Invoke-JsonApi -Method "POST" -Uri "$baseUrl/api/ml/predict-revenue" -Headers $headers -BodyObject $occBody
Assert-DataField $rev "predicted_revenue" "revenue prediction missing predicted_revenue"

Write-Host "[9/9] Predict cancellation..."
$cancel = Invoke-JsonApi -Method "POST" -Uri "$baseUrl/api/ml/predict-cancellation" -Headers $headers -BodyObject $occBody
Assert-DataField $cancel "predicted_cancellation_rate" "cancellation prediction missing predicted_cancellation_rate"

Write-Host "Smoke test passed: auth, standard ask, deep search, dashboard, decision support, and three ML predictions are available with explicit RAG retrieval/generation status."
