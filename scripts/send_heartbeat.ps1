param(
    [string]$ServerUrl = "http://127.0.0.1:8000",
    [string]$Token = "",
    [switch]$Quiet
)

$ErrorActionPreference = "Stop"

try {
    $computer = Get-CimInstance Win32_ComputerSystem -ErrorAction Stop
} catch {
    $computer = $null
}

try {
    $os = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
} catch {
    $os = $null
}

try {
    $cpu = Get-CimInstance Win32_Processor -ErrorAction Stop
} catch {
    $cpu = $null
}

try {
    $bios = Get-CimInstance Win32_BIOS -ErrorAction Stop
} catch {
    $bios = $null
}

try {
    $disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'" -ErrorAction Stop
} catch {
    $drive = Get-PSDrive -Name C
    $disk = [pscustomobject]@{
        Size = $drive.Used + $drive.Free
        FreeSpace = $drive.Free
    }
}

try {
    $network = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction Stop |
        Where-Object { $_.IPAddress -notlike "169.254*" -and $_.IPAddress -ne "127.0.0.1" } |
        Select-Object -First 1
} catch {
    $network = $null
}

$totalMemoryMb = if ($computer -and $computer.TotalPhysicalMemory) {
    [math]::Round($computer.TotalPhysicalMemory / 1MB)
} else {
    $null
}
$freeMemoryMb = if ($os -and $os.FreePhysicalMemory) {
    [math]::Round($os.FreePhysicalMemory / 1024)
} else {
    $null
}
$memoryPercent = if ($totalMemoryMb -and $totalMemoryMb -gt 0 -and $freeMemoryMb -ne $null) {
    [math]::Round((($totalMemoryMb - $freeMemoryMb) / $totalMemoryMb) * 100, 2)
} else {
    $null
}

$uptimeSeconds = if ($os -and $os.LastBootUpTime) {
    [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalSeconds)
} else {
    $null
}

$cpuPercent = if ($cpu) {
    [math]::Round(($cpu | Measure-Object -Property LoadPercentage -Average).Average, 2)
} else {
    $null
}

$payload = @{
    hostname = if ($env:COMPUTERNAME) { $env:COMPUTERNAME } else { [Environment]::MachineName }
    ip_address = if ($network) { $network.IPAddress } else { $null }
    username = if ($computer -and $computer.UserName) { $computer.UserName } else { "$env:USERDOMAIN\$env:USERNAME" }
    os_name = if ($os -and $os.Caption) { $os.Caption } else { [Environment]::OSVersion.VersionString }
    os_version = if ($os -and $os.Version) { $os.Version } else { [Environment]::OSVersion.Version.ToString() }
    manufacturer = if ($computer -and $computer.Manufacturer) { $computer.Manufacturer } else { $null }
    model = if ($computer -and $computer.Model) { $computer.Model } else { $null }
    serial_number = if ($bios -and $bios.SerialNumber) { $bios.SerialNumber } else { $null }
    cpu_count = if ($computer -and $computer.NumberOfLogicalProcessors) { $computer.NumberOfLogicalProcessors } else { [Environment]::ProcessorCount }
    total_memory_mb = $totalMemoryMb
    cpu_percent = $cpuPercent
    memory_percent = $memoryPercent
    disk_total_gb = [math]::Round($disk.Size / 1GB, 2)
    disk_free_gb = [math]::Round($disk.FreeSpace / 1GB, 2)
    uptime_seconds = $uptimeSeconds
} | ConvertTo-Json

$headers = @{}
if ($Token) {
    $headers["X-Agent-Token"] = $Token
}

try {
    Invoke-WebRequest -UseBasicParsing -Uri $ServerUrl -Method Get -TimeoutSec 5 | Out-Null
} catch {
    if (-not $Quiet) {
        Write-Host "Nao foi possivel conectar ao Astoria Monitor em $ServerUrl." -ForegroundColor Red
        Write-Host "Abra outro PowerShell nesta pasta e rode primeiro:" -ForegroundColor Yellow
        Write-Host "  .\scripts\run_dev.ps1" -ForegroundColor Yellow
        Write-Host "Quando aparecer 'Uvicorn running on http://127.0.0.1:8000', execute este coletor novamente." -ForegroundColor Yellow
    }
    exit 1
}

Invoke-RestMethod -Method Post -Uri "$ServerUrl/api/agent/heartbeat" -ContentType "application/json" -Headers $headers -Body $payload
