; SuperLocalMemory V2 Inno Setup Installer Script
; Copyright (c) 2026 Varun Pratap Bhardwaj
; Licensed under MIT License
; Repository: https://github.com/varun369/SuperLocalMemoryV2
;
; ATTRIBUTION REQUIRED: This notice must be preserved in all copies.

#define MyAppName "SuperLocalMemory V2"
#define MyAppVersion "2.1.0"
#define MyAppPublisher "Varun Pratap Bhardwaj"
#define MyAppURL "https://github.com/varun369/SuperLocalMemoryV2"
#define MyAppExeName "slm.cmd"
#define MyAppDescription "Universal AI Memory System - Local First"

[Setup]
; Basic app information
AppId={{8D5B7A9E-2F4C-4B6D-8A3E-9F1C5D7A2B4E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/issues
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
InfoBeforeFile=docs\WINDOWS-INSTALL-README.txt
InfoAfterFile=docs\WINDOWS-POST-INSTALL.txt
OutputDir=dist
OutputBaseFilename=SuperLocalMemory-Setup-v{#MyAppVersion}-windows
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Visual styling
WizardImageFile=assets\installer-banner.bmp
WizardSmallImageFile=assets\installer-icon.bmp

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "addtopath"; Description: "Add to PATH environment variable"; GroupDescription: "System Integration:"; Flags: checkedonce
Name: "startmenu"; Description: "Create Start Menu shortcuts"; GroupDescription: "Shortcuts:"; Flags: checkedonce
Name: "runinstaller"; Description: "Run installation script after setup"; GroupDescription: "Configuration:"; Flags: checkedonce

[Files]
; Core installer
Source: "install.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "ATTRIBUTION.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "CHANGELOG.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "QUICKSTART.md"; DestDir: "{app}"; Flags: ignoreversion

; Python source files
Source: "src\*"; DestDir: "{app}\src"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "mcp_server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "ui_server.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "api_server.py"; DestDir: "{app}"; Flags: ignoreversion

; CLI tools
Source: "bin\*"; DestDir: "{app}\bin"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "bin\slm.bat"; DestDir: "{app}\bin"; Flags: ignoreversion

; Configuration templates
Source: "configs\*"; DestDir: "{app}\configs"; Flags: ignoreversion recursesubdirs createallsubdirs

; Skills
Source: "skills\*"; DestDir: "{app}\skills"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "install-skills.sh"; DestDir: "{app}"; Flags: ignoreversion

; Shell completions (optional)
Source: "completions\*"; DestDir: "{app}\completions"; Flags: ignoreversion recursesubdirs createallsubdirs

; Requirements files
Source: "requirements*.txt"; DestDir: "{app}"; Flags: ignoreversion

; Verification scripts
Source: "verify-install.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "start-dashboard.ps1"; DestDir: "{app}"; Flags: ignoreversion

; Documentation
Source: "docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs

; UI assets (if present)
Source: "ui\*"; DestDir: "{app}\ui"; Flags: ignoreversion recursesubdirs createallsubdirs

; Helper scripts for Windows
Source: "bin\slm.cmd"; DestDir: "{app}\bin"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/k ""{app}\bin\slm.cmd"" status"; Comment: "SuperLocalMemory CLI"; IconFilename: "{app}\assets\icon.ico"
Name: "{group}\Dashboard"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\start-dashboard.ps1"""; Comment: "Open Web Dashboard"; WorkingDir: "{app}"
Name: "{group}\Documentation"; Filename: "{app}\README.md"; Comment: "Read Documentation"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"; Comment: "Uninstall SuperLocalMemory V2"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{cmd}"; Parameters: "/k ""{app}\bin\slm.cmd"" status"; Tasks: desktopicon; Comment: "SuperLocalMemory CLI"; IconFilename: "{app}\assets\icon.ico"

[Run]
; Run installer after setup completes
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\install.ps1"""; WorkingDir: "{app}"; StatusMsg: "Installing SuperLocalMemory V2..."; Tasks: runinstaller; Flags: runhidden

; Verification after installation
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\verify-install.ps1"""; WorkingDir: "{app}"; StatusMsg: "Verifying installation..."; Tasks: runinstaller; Flags: runhidden postinstall skipifsilent

; Offer to view README
Filename: "{app}\README.md"; Description: "View README"; Flags: postinstall shellexec skipifsilent unchecked

; Offer to launch dashboard
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\start-dashboard.ps1"""; Description: "Launch Dashboard"; Flags: postinstall nowait skipifsilent unchecked

[Code]
const
  EnvironmentKey = 'Environment';

var
  PythonInstalled: Boolean;
  PythonVersion: String;
  GitInstalled: Boolean;

{ Check if Python 3.8+ is installed }
function IsPythonInstalled: Boolean;
var
  ResultCode: Integer;
  Output: AnsiString;
  TempFile: String;
begin
  Result := False;
  TempFile := ExpandConstant('{tmp}\python_version.txt');

  { Try python command }
  if Exec('cmd.exe', '/c python --version > "' + TempFile + '" 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if FileExists(TempFile) then
    begin
      LoadStringFromFile(TempFile, Output);
      if Pos('Python 3.', Output) > 0 then
      begin
        Result := True;
        PythonVersion := Trim(Output);
        DeleteFile(TempFile);
        Exit;
      end;
    end;
  end;

  { Try python3 command }
  if Exec('cmd.exe', '/c python3 --version > "' + TempFile + '" 2>&1', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    if FileExists(TempFile) then
    begin
      LoadStringFromFile(TempFile, Output);
      if Pos('Python 3.', Output) > 0 then
      begin
        Result := True;
        PythonVersion := Trim(Output);
        DeleteFile(TempFile);
        Exit;
      end;
    end;
  end;

  if FileExists(TempFile) then
    DeleteFile(TempFile);
end;

{ Check if Git is installed }
function IsGitInstalled: Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/c git --version', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Result then
    Result := (ResultCode = 0);
end;

{ Initialize setup - check prerequisites }
function InitializeSetup(): Boolean;
var
  ErrorMessage: String;
begin
  Result := True;
  ErrorMessage := '';

  { Check Python }
  PythonInstalled := IsPythonInstalled;
  if not PythonInstalled then
  begin
    ErrorMessage := 'Python 3.8 or higher is required but not found.' + #13#10 + #13#10 +
                    'Please install Python from: https://www.python.org/downloads/' + #13#10 + #13#10 +
                    'Make sure to check "Add Python to PATH" during installation.' + #13#10 + #13#10 +
                    'Continue anyway? (Installation may fail)';

    if MsgBox(ErrorMessage, mbError, MB_YESNO) = IDNO then
    begin
      Result := False;
      Exit;
    end;
  end;

  { Check Git (optional) }
  GitInstalled := IsGitInstalled;
  if not GitInstalled then
  begin
    MsgBox('Git is not installed (optional).' + #13#10 + #13#10 +
           'Some features may require Git.' + #13#10 + #13#10 +
           'Download from: https://git-scm.com/download/win', mbInformation, MB_OK);
  end;
end;

{ Display welcome message with system information }
function NextButtonClick(CurPageID: Integer): Boolean;
var
  Message: String;
begin
  Result := True;

  if CurPageID = wpWelcome then
  begin
    Message := 'System Check:' + #13#10 + #13#10;

    if PythonInstalled then
      Message := Message + '✓ Python: ' + PythonVersion + #13#10
    else
      Message := Message + '✗ Python: Not found (REQUIRED)' + #13#10;

    if GitInstalled then
      Message := Message + '✓ Git: Installed' + #13#10
    else
      Message := Message + '○ Git: Not installed (optional)' + #13#10;

    Message := Message + #13#10 + 'Installation will:' + #13#10 +
               '• Copy files to: ' + ExpandConstant('{app}') + #13#10 +
               '• Install to: %USERPROFILE%\.claude-memory\' + #13#10 +
               '• Configure MCP for IDEs' + #13#10 +
               '• Install universal skills' + #13#10 +
               '• Add CLI to system' + #13#10;

    MsgBox(Message, mbInformation, MB_OK);
  end;
end;

{ Add to PATH environment variable }
procedure AddToPath;
var
  OldPath: String;
  NewPath: String;
  BinPath: String;
begin
  BinPath := ExpandConstant('{app}\bin');

  { Get current PATH }
  if RegQueryStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', OldPath) then
  begin
    { Check if already in PATH }
    if Pos(Uppercase(BinPath), Uppercase(OldPath)) = 0 then
    begin
      { Add to PATH }
      if OldPath <> '' then
        NewPath := OldPath + ';' + BinPath
      else
        NewPath := BinPath;

      RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', NewPath);

      { Broadcast WM_SETTINGCHANGE message }
      SendBroadcastNotifyMessage('Environment', 0);
    end;
  end
  else
  begin
    { PATH doesn't exist, create it }
    RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', BinPath);
    SendBroadcastNotifyMessage('Environment', 0);
  end;
end;

{ Remove from PATH on uninstall }
procedure RemoveFromPath;
var
  OldPath: String;
  NewPath: String;
  BinPath: String;
  PathArray: TArrayOfString;
  I: Integer;
begin
  BinPath := ExpandConstant('{app}\bin');

  if RegQueryStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', OldPath) then
  begin
    NewPath := '';
    PathArray := SplitString(OldPath, ';');

    for I := 0 to GetArrayLength(PathArray) - 1 do
    begin
      if Uppercase(Trim(PathArray[I])) <> Uppercase(BinPath) then
      begin
        if NewPath <> '' then
          NewPath := NewPath + ';';
        NewPath := NewPath + PathArray[I];
      end;
    end;

    RegWriteStringValue(HKEY_CURRENT_USER, EnvironmentKey, 'Path', NewPath);
    SendBroadcastNotifyMessage('Environment', 0);
  end;
end;

{ After install }
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if IsTaskSelected('addtopath') then
      AddToPath;
  end;
end;

{ Uninstall }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    RemoveFromPath;

    { Ask to remove user data }
    if MsgBox('Remove all SuperLocalMemory data from %USERPROFILE%\.claude-memory?' + #13#10 + #13#10 +
              'This will delete:' + #13#10 +
              '• All memories (memory.db)' + #13#10 +
              '• Configuration files' + #13#10 +
              '• Learned patterns' + #13#10 + #13#10 +
              'WARNING: This cannot be undone!', mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{%USERPROFILE}\.claude-memory'), True, True, True);
    end;
  end;
end;

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
