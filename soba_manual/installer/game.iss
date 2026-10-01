; UTF-8 installer source. Keep AppId and save location stable across updates.
#ifndef GameVersion
  #define GameVersion "1.3.1"
#endif
#define GameName "Quán Mì Của Tôi"
#define GameExe "Quán Mì Của Tôi.exe"
#define GamePublisher "Đỗ Văn Phi"

[Setup]
AppId={{95BC9684-36DF-4C0F-9E18-675254660C42}
AppName={#GameName}
AppVersion={#GameVersion}
AppPublisher={#GamePublisher}
AppPublisherURL=https://github.com/dovanphit1-creator/Qu-n-soba
AppSupportURL=https://github.com/dovanphit1-creator/Qu-n-soba/issues
AppUpdatesURL=https://github.com/dovanphit1-creator/Qu-n-soba/releases
DefaultDirName={localappdata}\Programs\QuanMiCuaToi
DefaultGroupName={#GameName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\installer-output
OutputBaseFilename=QuanMiCuaToi-Setup
SetupIconFile=..\assets\game.ico
UninstallDisplayIcon={app}\{#GameExe}
VersionInfoVersion={#GameVersion}.0
VersionInfoCompany={#GamePublisher}
VersionInfoProductName={#GameName}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=no
RestartApplications=no
UsePreviousAppDir=yes
UsePreviousTasks=yes

[Messages]
ButtonNext=Tiếp >
ButtonBack=< Quay lại
ButtonInstall=Cài đặt
ButtonCancel=Hủy
ButtonFinish=Hoàn tất
WelcomeLabel1=Chào mừng đến với [name]
WelcomeLabel2=Bộ cài sẽ cài [name/ver] trên máy của bạn.%n%nNếu game đang mở, bộ cài sẽ yêu cầu game lưu và thoát trước khi cập nhật. Tiến trình chơi được giữ nguyên. Bấm Tiếp để tiếp tục.
FinishedHeadingLabel=Đã cài đặt [name]
FinishedLabel=Game đã được cài trên máy. Bạn có thể mở game bằng biểu tượng trên Desktop hoặc trong menu Start.

[Tasks]
Name: "desktopicon"; Description: "Tạo biểu tượng trên Desktop"; GroupDescription: "Biểu tượng game:"

[Files]
Source: "close-running-game.ps1"; Flags: dontcopy
Source: "..\..\dist\{#GameExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\HUONG_DAN.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\PHAT_HANH.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\dist\SHA256.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#GameName}"; Filename: "{app}\{#GameExe}"; WorkingDir: "{app}"; AppUserModelID: "QuanMiCuaToi.Game"
Name: "{autodesktop}\{#GameName}"; Filename: "{app}\{#GameExe}"; WorkingDir: "{app}"; AppUserModelID: "QuanMiCuaToi.Game"; Tasks: desktopicon

[Run]
Filename: "{app}\{#GameExe}"; Description: "Mở {#GameName}"; Flags: nowait postinstall skipifsilent

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ExitCode: Integer;
  Helper, Params: String;
begin
  Result := '';
  ExtractTemporaryFile('close-running-game.ps1');
  Helper := ExpandConstant('{tmp}\close-running-game.ps1');
  Params := '-NoProfile -NonInteractive -ExecutionPolicy Bypass -File "' +
    Helper + '" -GamePath "' + ExpandConstant('{app}\{#GameExe}') + '"';
  WizardForm.StatusLabel.Caption := 'Đang yêu cầu game lưu tiến trình và thoát để cập nhật...';
  if not Exec(ExpandConstant('{sys}\WindowsPowerShell\v1.0\powershell.exe'),
    Params, '', SW_HIDE, ewWaitUntilTerminated, ExitCode) then
    Result := 'Không thể yêu cầu game thoát. Hãy đóng game rồi bấm Thử lại.'
  else if ExitCode <> 0 then
    Result := 'Game chưa thoát nên chưa thay tệp. Hãy lưu và đóng game rồi bấm Thử lại.';
end;
