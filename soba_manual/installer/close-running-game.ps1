param([Parameter(Mandatory=$true)][string]$GamePath)
$ErrorActionPreference = 'Stop'
try {
  $target = [IO.Path]::GetFullPath($GamePath)
  $session = (Get-Process -Id $PID).SessionId
  # 1.2+ may have a hidden tray window. Ask it to save and quit using scoped IPC.
  $requestDir = Join-Path $env:LOCALAPPDATA 'QuanSobaManual'
  New-Item -ItemType Directory -Force -Path $requestDir | Out-Null
  $request = @{exe=$target;at=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()} | ConvertTo-Json -Compress
  [IO.File]::WriteAllText((Join-Path $requestDir 'shutdown-request.json'),$request,[Text.UTF8Encoding]::new($false))
  $sent = @{}
  $deadline = [DateTime]::UtcNow.AddSeconds(45)
  do {
    $active = @(Get-Process | Where-Object {
      try { $_.SessionId -eq $session -and $_.Path -and [string]::Equals($_.Path,$target,[StringComparison]::OrdinalIgnoreCase) }
      catch { $false }
    })
    if ($active.Count -eq 0) { exit 0 }
    foreach ($game in $active) {
      $game.Refresh()
      if ($game.MainWindowHandle -ne 0 -and -not $sent.ContainsKey($game.Id)) {
        if ($game.CloseMainWindow()) { $sent[$game.Id] = $true }
      }
    }
    Start-Sleep -Milliseconds 250
  } while ([DateTime]::UtcNow -lt $deadline)
  # Never kill the game: its normal quit handler must save before exiting.
  exit 1
} catch { exit 2 }
