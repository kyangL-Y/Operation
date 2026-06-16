$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot

Write-Host "Stopping previous demo processes..."
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue |
  Where-Object { $_.LocalPort -in @(5000, 5173, 8080) } |
  Select-Object -ExpandProperty OwningProcess -Unique |
  ForEach-Object {
    Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue
  }

try {
  Get-CimInstance Win32_Process -ErrorAction Stop |
    Where-Object {
      ($_.Name -in @("python.exe", "java.exe", "node.exe", "powershell.exe")) -and
      $_.CommandLine -and
      $_.CommandLine.Contains($projectRoot)
    } |
    ForEach-Object {
      Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
    }
} catch {
  Write-Warning "Process command-line cleanup skipped: $($_.Exception.Message)"
}

Start-Sleep -Seconds 2

Write-Host "Starting ML service..."
$deepseekEnvPath = Join-Path $PSScriptRoot "deepseek.env"
$mlPythonPath = Join-Path $PSScriptRoot "ml/.venv/Scripts/python.exe"
if (-not (Test-Path -LiteralPath $mlPythonPath)) {
  $mlPythonPath = Join-Path $PSScriptRoot ".venv_ml/Scripts/python.exe"
}
if (-not (Test-Path -LiteralPath $mlPythonPath)) {
  $mlPythonPath = "python"
}
$mlCommand = @'
function Import-LocalEnvFile {
  param([string]$Path)
  if (-not (Test-Path -LiteralPath $Path)) {
    return
  }
  Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) {
      return
    }
    $name, $value = $line.Split("=", 2)
    $name = $name.Trim()
    $value = $value.Trim().Trim('"').Trim("'")
    if ($name) {
      [Environment]::SetEnvironmentVariable($name, $value, "Process")
    }
  }
}

Import-LocalEnvFile -Path '__DEEPSEEK_ENV_PATH__'

if (-not $env:CHAT_API_KEY -and $env:DEEPSEEK_API_KEY) {
  $env:CHAT_API_KEY = $env:DEEPSEEK_API_KEY
}
if (-not $env:CHAT_BASE_URL) {
  if ($env:DEEPSEEK_BASE_URL) {
    $env:CHAT_BASE_URL = $env:DEEPSEEK_BASE_URL
  } else {
    $env:CHAT_BASE_URL = 'https://api.deepseek.com'
  }
}
if (-not $env:CHAT_MODEL) {
  if ($env:DEEPSEEK_MODEL) {
    $env:CHAT_MODEL = $env:DEEPSEEK_MODEL
  } else {
    $env:CHAT_MODEL = 'deepseek-chat'
  }
}
& '__ML_PYTHON_PATH__' -X utf8 api_server.py
'@.Replace('__DEEPSEEK_ENV_PATH__', $deepseekEnvPath.Replace("'", "''")).Replace('__ML_PYTHON_PATH__', $mlPythonPath.Replace("'", "''"))
$mlScriptPath = Join-Path $PSScriptRoot ".ml_start.ps1"
Set-Content -Path $mlScriptPath -Value $mlCommand -Encoding UTF8
Start-Process powershell -WorkingDirectory "$PSScriptRoot/ml" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-File", $mlScriptPath

Write-Host "Starting backend..."
$backendCommand = @'
Set-Location '__BACKEND_DIR__'
if (-not (Test-Path 'target/classes')) {
  mvn -q -DskipTests package
  if ($LASTEXITCODE -ne 0) { throw 'Backend package failed' }
}
mvn -q -DskipTests dependency:build-classpath '-Dmdep.outputFile=target/classpath.txt'
if ($LASTEXITCODE -ne 0) { throw 'Backend classpath build failed' }
$classPath = 'target/classes;' + (Get-Content 'target/classpath.txt' -ErrorAction Stop)
& java '-Dserver.port=8080' '-cp' $classPath 'com.hotel.ops.HotelOpsApplication'
'@.Replace('__BACKEND_DIR__', $PSScriptRoot.Replace("'", "''") + "/backend")
$backendScriptPath = Join-Path $PSScriptRoot ".backend_start.ps1"
Set-Content -Path $backendScriptPath -Value $backendCommand -Encoding UTF8
Start-Process powershell -WorkingDirectory "$PSScriptRoot/backend" -ArgumentList "-NoProfile", "-ExecutionPolicy", "Bypass", "-NoExit", "-File", $backendScriptPath

Write-Host "Starting frontend..."
Start-Process cmd.exe -WorkingDirectory "$PSScriptRoot/frontend" -ArgumentList "/k", "set VITE_PROXY_TARGET=http://localhost:8080&& set VITE_API_BASE_URL=http://localhost:8080/api&& npm run dev -- --host=0.0.0.0 --port=5173 --strictPort"

Write-Host "Started. Frontend: http://localhost:5173  Backend: http://localhost:8080  ML: http://localhost:5000"
