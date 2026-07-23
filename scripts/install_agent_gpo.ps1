param(
    [Parameter(Mandatory = $true)]
    [string]$ServerUrl,

    [string]$Token = "",

    [int]$IntervalMinutes = 5,

    [string]$InstallDir = "$env:ProgramData\AstoriaMonitor"
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 1) {
    throw "IntervalMinutes deve ser maior ou igual a 1."
}

$sourceAgent = Join-Path $PSScriptRoot "send_heartbeat.ps1"
if (-not (Test-Path $sourceAgent)) {
    throw "Nao foi possivel localizar o coletor: $sourceAgent"
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

$agentPath = Join-Path $InstallDir "send_heartbeat.ps1"
$configPath = Join-Path $InstallDir "agent.config.json"
$runnerPath = Join-Path $InstallDir "run_agent.ps1"
$logPath = Join-Path $InstallDir "agent.log"

Copy-Item -Path $sourceAgent -Destination $agentPath -Force

@{
    server_url = $ServerUrl.TrimEnd("/")
    token = $Token
    interval_minutes = $IntervalMinutes
    installed_at = (Get-Date).ToString("s")
} | ConvertTo-Json | Set-Content -Path $configPath -Encoding UTF8

@'
$ErrorActionPreference = "Stop"

$baseDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $baseDir "agent.config.json"
$agentPath = Join-Path $baseDir "send_heartbeat.ps1"
$logPath = Join-Path $baseDir "agent.log"

try {
    $config = Get-Content -Path $configPath -Raw | ConvertFrom-Json
    & $agentPath -ServerUrl $config.server_url -Token $config.token -Quiet
    "$(Get-Date -Format s) coleta enviada para $($config.server_url)" | Add-Content -Path $logPath
} catch {
    "$(Get-Date -Format s) erro na coleta: $($_.Exception.Message)" | Add-Content -Path $logPath
    exit 1
}
'@ | Set-Content -Path $runnerPath -Encoding UTF8

$acl = Get-Acl $InstallDir
$acl.SetAccessRuleProtection($true, $false)
$systemAccount = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-18")
$administratorsGroup = New-Object System.Security.Principal.SecurityIdentifier("S-1-5-32-544")
$rules = @(
    New-Object System.Security.AccessControl.FileSystemAccessRule($systemAccount, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow"),
    New-Object System.Security.AccessControl.FileSystemAccessRule($administratorsGroup, "FullControl", "ContainerInherit,ObjectInherit", "None", "Allow")
)
foreach ($rule in $rules) {
    $acl.AddAccessRule($rule)
}
Set-Acl -Path $InstallDir -AclObject $acl

$taskName = "Astoria Monitor Agent"
$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$runnerPath`""
$trigger = New-ScheduledTaskTrigger `
    -Once `
    -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) `
    -RepetitionDuration (New-TimeSpan -Days 3650)
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 2)

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Principal $principal `
    -Settings $settings `
    -Force | Out-Null

Start-ScheduledTask -TaskName $taskName

Write-Host "Agente Astoria Monitor instalado em $InstallDir"
Write-Host "Tarefa agendada: $taskName"
Write-Host "Servidor: $ServerUrl"
