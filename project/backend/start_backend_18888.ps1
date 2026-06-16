$ErrorActionPreference = "Stop"

$backendRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $backendRoot
$logDir = Join-Path $projectRoot "logs"
$logPath = Join-Path $logDir "backend-18888.log"

if (!(Test-Path -LiteralPath $logDir)) {
  New-Item -ItemType Directory -Path $logDir -Force | Out-Null
}

Set-Location $backendRoot

if (-not (Test-Path -LiteralPath "target/classes")) {
  mvn -q -DskipTests package
  if ($LASTEXITCODE -ne 0) {
    throw "Backend package failed."
  }
}

mvn -q -DskipTests dependency:build-classpath "-Dmdep.outputFile=target/classpath.txt"
if ($LASTEXITCODE -ne 0) {
  throw "Failed to build backend classpath."
}

$classpath = "target/classes;" + (Get-Content -Raw -Encoding UTF8 -LiteralPath "target/classpath.txt").Trim()
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
"[$timestamp] starting backend on 18888" | Out-File -FilePath $logPath -Encoding UTF8 -Append
& java "-Dserver.port=18888" "-cp" $classpath "com.hotel.ops.HotelOpsApplication" *>> $logPath
