$ErrorActionPreference = 'Stop'
$setup = Join-Path $PWD 'installer-output\QuanMiCuaToi-Setup.exe'
$installDir = Join-Path $env:LOCALAPPDATA 'Programs\QuanMiCuaToi'
$saveDir = Join-Path $env:LOCALAPPDATA 'QuanSobaManual'
$save = Join-Path $saveDir 'save-vnd.json'
$desktop = Join-Path ([Environment]::GetFolderPath('Desktop')) 'Quán Mì Của Tôi.lnk'
$start = Join-Path ([Environment]::GetFolderPath('Programs')) 'Quán Mì Của Tôi.lnk'
# This script runs only in the fresh, disposable GitHub-hosted build machine.
if ((Test-Path $installDir) -or (Test-Path $save)) { throw 'Expected a fresh verification profile' }
New-Item -ItemType Directory -Path $saveDir -Force | Out-Null
$env:PYTHONPATH = 'soba_manual'
python -c "from model import World,save_path; w=World(); w.cash=8765432; w.save(save_path())"
if ($LASTEXITCODE -ne 0) { throw 'Could not create verification save' }
$before = (Get-FileHash $save -Algorithm SHA256).Hash
function Assert-Save {
  if (-not (Test-Path $save) -or (Get-FileHash $save -Algorithm SHA256).Hash -ne $before) { throw 'Installer changed saved progress' }
}
function Install-Game {
  $p = Start-Process -FilePath $setup -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP- /TASKS=desktopicon' -Wait -PassThru
  if ($p.ExitCode -ne 0) { throw "Install failed: $($p.ExitCode)" }
  Assert-Save
  foreach ($file in @('Quán Mì Của Tôi.exe','HUONG_DAN.txt','PHAT_HANH.txt','SHA256.txt','unins000.exe')) {
    if (-not (Test-Path (Join-Path $installDir $file))) { throw "Missing installed file: $file" }
  }
  $shell = New-Object -ComObject WScript.Shell
  foreach ($link in @($desktop,$start)) {
    if (-not (Test-Path $link)) { throw "Missing shortcut: $link" }
    $shortcut=$shell.CreateShortcut($link)
    # Windows may resolve a shortcut using an 8.3 path; compare file identities.
    Write-Output ('Shortcut target: ' + $shortcut.TargetPath)
    $env:QUANMI_LINK_TARGET = [Environment]::ExpandEnvironmentVariables($shortcut.TargetPath)
    $env:QUANMI_INSTALLED_EXE = Join-Path $installDir 'Quán Mì Của Tôi.exe'
    python -c "import os; assert os.path.samefile(os.environ['QUANMI_LINK_TARGET'],os.environ['QUANMI_INSTALLED_EXE'])"
    if ($LASTEXITCODE -ne 0) { throw 'Incorrect shortcut target' }
  }
}
Install-Game
$exe = Join-Path $installDir 'Quán Mì Của Tôi.exe'
$report = Join-Path $PWD 'installed-game.json'
$p=Start-Process -FilePath $exe -ArgumentList @('--smoke-test',$report) -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Installed game failed smoke check' }
$r=Get-Content $report -Raw | ConvertFrom-Json
if (-not $r.ok -or -not $r.frozen) { throw 'Installed game report invalid' }
Assert-Save
Install-Game
$p=Start-Process -FilePath (Join-Path $installDir 'unins000.exe') -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Uninstall failed' }
Assert-Save
if ((Test-Path $exe) -or (Test-Path $desktop) -or (Test-Path $start)) { throw 'Uninstall did not remove application and shortcuts' }
@{ok=$true;checks=@('install','desktop-shortcut','start-menu-shortcut','installed-game-launch','reinstall','uninstall','saved-progress-preserved')} | ConvertTo-Json | Set-Content installer-verification.json -Encoding utf8
