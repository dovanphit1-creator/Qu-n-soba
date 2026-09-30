$ErrorActionPreference='Stop'
$installDir=Join-Path $env:LOCALAPPDATA 'Programs\QuanMiCuaToi'
$exe=Join-Path $installDir 'Quán Mì Của Tôi.exe'
$save=Join-Path $env:LOCALAPPDATA 'QuanSobaManual\save-vnd.json'
$oldSetup=Join-Path $PWD 'old-setup.exe'
Invoke-WebRequest 'https://github.com/dovanphit1-creator/Qu-n-soba/releases/download/1.1.0/QuanMiCuaToi-Setup.exe' -OutFile $oldSetup
$p=Start-Process $oldSetup -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Old version install failed' }
$env:PYTHONPATH='soba_manual'
@'
import json
from model import World,save_path
w=World(seed=42)
for name in ('Bát/đĩa','Mì tươi','Nước dùng','Hành'):w.restock(name,20)
w.open_shop();w.spawn_left=100000
p=w.add_party(1);w.respond(p.id,'accept');w.update(p.buy_seconds);w.collect(p.id);w.seat(p.id,0)
w.start_pot(0);w.cash=7654321;w.save(save_path())
data=json.loads(save_path().read_text(encoding='utf-8'))
data.pop('service_time_scale',None)
save_path().write_text(json.dumps(data),encoding='utf-8')
'@ | python -
if ($LASTEXITCODE -ne 0) { throw 'Could not create live shift fixture' }
$before=Get-Content $save -Raw | ConvertFrom-Json
Remove-Item Env:SDL_VIDEODRIVER -ErrorAction SilentlyContinue
$old=Start-Process $exe -PassThru
$visible=$false
for ($i=0;$i -lt 100;$i++) {
  $windows=@(Get-Process | Where-Object { $_.Path -eq $exe -and $_.MainWindowHandle -ne 0 })
  if ($windows.Count -gt 0) { $visible=$true;break }
  Start-Sleep -Milliseconds 200
}
if (-not $visible) { throw 'Old game window did not open' }
Start-Sleep -Seconds 2
$setup=Join-Path $PWD 'installer-output\QuanMiCuaToi-Setup.exe'
$p=Start-Process $setup -ArgumentList '/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /SP-' -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Update while old game running failed' }
if (@(Get-Process | Where-Object { $_.Path -eq $exe }).Count -ne 0) { throw 'Old game did not exit cleanly' }
$after=Get-Content $save -Raw | ConvertFrom-Json
if (-not $after.open -or $after.cash -ne 7654321 -or $after.parties[0].id -ne $before.parties[0].id) { throw 'Live shift progress was lost' }
if ($after.pots[0] -le $before.pots[0]) { throw 'Normal game shutdown did not save elapsed cooking' }
$new=Start-Process $exe -PassThru
Start-Sleep -Seconds 4
& powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File soba_manual/installer/close-running-game.ps1 -GamePath $exe
if ($LASTEXITCODE -ne 0) { throw 'New game could not close gracefully' }
$resumed=Get-Content $save -Raw | ConvertFrom-Json
if (-not $resumed.open -or $resumed.cash -ne 7654321 -or $resumed.parties[0].id -ne $before.parties[0].id) { throw 'New game did not resume the old shift' }
@{ok=$true;checks=@('released-old-game-running','installer-graceful-close','live-shift-saved','no-force-kill','new-game-resumes-shift')} | ConvertTo-Json | Set-Content live-upgrade-verification.json -Encoding utf8
