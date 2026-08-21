#define MyAppName "Outlook OTP Autofill"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "INNOCEAN"

[Setup]
AppId={{8D02FDC5-B81C-44D7-89AB-E80C3570F18A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\OutlookOtpAutofill
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=OutlookOtpAutofillSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no
UninstallDisplayIcon={app}\otp_diagnostics.exe

[Dirs]
Name: "{app}\logs"

[Tasks]
Name: "autostart"; Description: "Windows 로그인 시 자동 시작"; GroupDescription: "추가 옵션:"; Flags: checkedonce

[Files]
Source: "..\dist\otp_autofill.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\chrome_watcher.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\otp_diagnostics.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
Name: "{group}\Outlook 진단"; Filename: "{app}\otp_diagnostics.exe"; Parameters: "--diagnose-outlook"; WorkingDir: "{app}"
Name: "{group}\Chrome 진단"; Filename: "{app}\otp_diagnostics.exe"; Parameters: "--diagnose-chrome --diagnose-delay 5"; WorkingDir: "{app}"
Name: "{userstartup}\Outlook OTP Autofill"; Filename: "{app}\chrome_watcher.exe"; WorkingDir: "{app}"; Comment: "Start Outlook OTP Autofill while Chrome is running"; Tasks: autostart

[Run]
Filename: "{app}\chrome_watcher.exe"; Description: "{#MyAppName} 시작"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\logs"
Type: dirifempty; Name: "{app}"
