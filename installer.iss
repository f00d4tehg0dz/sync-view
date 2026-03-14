; Sync View - Inno Setup Installer Script
; Requires Inno Setup 6+ (https://jrsoftware.org/isinfo.php)
; Compile with: ISCC.exe installer.iss

#define MyAppName "Sync View"
#define MyAppVersion "3.0.0"
#define MyAppPublisher "Sync View"
#define MyAppURL "https://github.com/f00d4tehg0dz"
#define MyAppExeName "SyncView.exe"

[Setup]
AppId={{8F3D2A1B-5C7E-4D9F-A2B1-6E8F3C4D5A7B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer_output
OutputBaseFilename=SyncView-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=icons\icon.ico
UninstallDisplayIcon={app}\SyncView.exe
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startup"; Description: "Start with Windows"; GroupDescription: "Startup:"
Name: "registerhost"; Description: "Register Firefox native messaging host"; GroupDescription: "Browser integration:"

[Files]
; Main application
Source: "dist\SyncView.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\host.exe"; DestDir: "{app}"; Flags: ignoreversion

; Extension files
Source: "dist\extension\*"; DestDir: "{app}\extension"; Flags: ignoreversion recursesubdirs createallsubdirs

; Icon for the app
Source: "icons\icon-48.png"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; Native messaging host manifest registration
Root: HKCU; Subkey: "Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc"; ValueType: string; ValueData: "{app}\youtube_discord_rpc.json"; Flags: uninsdeletekey; Tasks: registerhost

; Startup entry
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "SyncView"; ValueData: """{app}\{#MyAppExeName}"" --minimized"; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/f /im SyncView.exe"; Flags: runhidden; RunOnceId: "KillApp"
Filename: "taskkill"; Parameters: "/f /im host.exe"; Flags: runhidden; RunOnceId: "KillHost"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\youtube_discord_rpc.json"

[Code]
procedure CreateNativeManifest;
var
  ManifestPath, HostPath, Content: String;
begin
  HostPath := ExpandConstant('{app}\host.exe');
  ManifestPath := ExpandConstant('{app}\youtube_discord_rpc.json');

  // Escape backslashes for JSON
  StringChangeEx(HostPath, '\', '\\', True);

  Content := '{' + #13#10 +
    '  "name": "youtube_discord_rpc",' + #13#10 +
    '  "description": "Sync View native messaging host",' + #13#10 +
    '  "path": "' + HostPath + '",' + #13#10 +
    '  "type": "stdio",' + #13#10 +
    '  "allowed_extensions": ["sync-view@example.com"]' + #13#10 +
    '}';

  SaveStringToFile(ManifestPath, Content, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if IsTaskSelected('registerhost') then
      CreateNativeManifest;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Clean up registry
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, 'Software\Mozilla\NativeMessagingHosts\youtube_discord_rpc');
    RegDeleteValue(HKEY_CURRENT_USER, 'Software\Microsoft\Windows\CurrentVersion\Run', 'SyncView');
    // Clean up AppData config
    DelTree(ExpandConstant('{userappdata}\SyncView'), True, True, True);
  end;
end;
