$ErrorActionPreference='Stop'
$msi=Join-Path $PWD 'espeak-ng.msi'
Invoke-WebRequest 'https://github.com/espeak-ng/espeak-ng/releases/download/1.52.0/espeak-ng.msi' -OutFile $msi
if ((Get-FileHash $msi -Algorithm SHA256).Hash.ToLower() -ne '7f673c709ea5dd579d3b5ebb98688cc575328a6ab7438d2bc405b88cedaeafb9') { throw 'Unexpected speech engine bytes' }
$extract=Join-Path $PWD 'speech-extract'
$p=Start-Process msiexec.exe -ArgumentList @('/a',"`"$msi`"",'/qn',"TARGETDIR=`"$extract`"") -Wait -PassThru
if ($p.ExitCode -ne 0) { throw 'Could not extract speech engine' }
$binary=Get-ChildItem $extract -Recurse -Filter espeak-ng.exe | Select-Object -First 1
if (-not $binary) { throw 'Missing speech executable' }
$dest=Join-Path $PWD 'soba_manual\assets\speech'
New-Item $dest -ItemType Directory -Force | Out-Null
Copy-Item (Join-Path $binary.Directory.FullName '*') $dest -Recurse -Force
$machine=python -c "import pefile; print(pefile.PE(r'$($binary.FullName)').FILE_HEADER.Machine)"
$runtimeDir=if ($machine -eq '332') { Join-Path $env:WINDIR 'SysWOW64' } else { Join-Path $env:WINDIR 'System32' }
foreach ($dll in @('vcruntime140.dll','vcruntime140_1.dll','msvcp140.dll','concrt140.dll')) {
  $file=Join-Path $runtimeDir $dll
  if (Test-Path $file) { Copy-Item $file $dest -Force }
}
$data=Join-Path $dest 'espeak-ng-data' 
if (-not (Test-Path $data)) { throw 'Missing voice data' }
Get-ChildItem $data -Filter '*_dict' | Where-Object { $_.Name -notin @('vi_dict','en_dict') } | Remove-Item
Invoke-WebRequest 'https://raw.githubusercontent.com/espeak-ng/espeak-ng/1.52.0/COPYING' -OutFile (Join-Path $dest 'COPYING')
Set-Content (Join-Path $dest 'SOURCES.txt') -Encoding utf8 -Value 'eSpeak NG 1.52.0, GPL-3.0. Source: https://github.com/espeak-ng/espeak-ng/tree/1.52.0 ; full source archive: https://github.com/espeak-ng/espeak-ng/archive/refs/tags/1.52.0.tar.gz'
$env:PYTHONPATH='soba_manual'
@'
import wave,io
from audio import render_vi
b=render_vi('Phiếu nhóm một. Mì soba trứng, trà xanh, bò húc. Món tự tạo của tôi.')
with wave.open(io.BytesIO(b)) as w:
    assert w.getnframes()>22050 and w.getframerate()>0
print('PASS: bundled Vietnamese engine synthesizes standard and custom dish names without a system voice.')
'@ | python -
if ($LASTEXITCODE -ne 0) { throw 'Vietnamese voice verification failed' }
