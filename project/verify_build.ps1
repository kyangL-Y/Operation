$ErrorActionPreference = "Stop"

function Assert-LastExitCode($step) {
  if ($LASTEXITCODE -ne 0) {
    throw "$step failed with exit code $LASTEXITCODE"
  }
}

Write-Host "ML: syntax check..."
Set-Location "$PSScriptRoot/ml"
python -m py_compile api_server.py train_prediction.py dataset_loader.py
Assert-LastExitCode "ML syntax check"

Write-Host "Backend: run tests and compile..."
Set-Location "$PSScriptRoot/backend"
mvn -q test
Assert-LastExitCode "Backend tests"
mvn -q -DskipTests compile
Assert-LastExitCode "Backend compile"

Write-Host "Frontend: build..."
Set-Location "$PSScriptRoot/frontend"
npm run build
Assert-LastExitCode "Frontend build"

Write-Host "Verification done."
