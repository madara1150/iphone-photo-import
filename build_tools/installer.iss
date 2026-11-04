; Inno Setup 6.5+ script -> dist\iPhonePhotoImport-Windows-Setup.exe
; Build: ISCC /DAppVersion=1.2.3 build_tools\installer.iss
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppName "iPhone Photo Import"
#define AppExe "iPhonePhotoImport.exe"
#define AppURL "https://github.com/madara1150/iphone-photo-import"

[Setup]
AppId={{F59878C0-38CC-4B89-BD11-DC069DB3EA17}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=Tanathip
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases
DefaultDirName={autopf}\iPhone Photo Import
DefaultGroupName=iPhone Photo Import
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=iPhonePhotoImport-Windows-Setup
SetupIconFile=..\assets\icon.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
Compression=lzma2/ultra64
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=yes
WizardStyle=modern
ShowLanguageDialog=auto
LanguageDetectionMethod=uilanguage
VersionInfoVersion={#AppVersion}
VersionInfoCompany=Tanathip
VersionInfoDescription={#AppName} Setup
VersionInfoProductName={#AppName}
VersionInfoCopyright=Copyright (c) 2026 Tanathip

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "thai"; MessagesFile: "compiler:Languages\Thai.isl"

[Messages]
english.FinishedLabel=Plug in your iPhone, unlock it and tap "Trust". Needs the free "Apple Devices" app (or iTunes) from the Microsoft Store.
thai.FinishedLabel=เสียบสาย iPhone ปลดล็อก แล้วกด "เชื่อถือ" (Trust) — ต้องมีแอป "Apple Devices" (หรือ iTunes) จาก Microsoft Store ในเครื่อง

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "..\dist\iPhonePhotoImport\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\iPhone Photo Import"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\iPhone Photo Import"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
