; Inno Setup script for Call Switcher on Windows; build with build-windows.ps1, which passes
; AppVersion (e.g. 0.1.0rc2) and NumericVersion (e.g. 0.1.0).
;
; Installs per user (no admin rights) and registers Call Switcher for tel:, callto: and sip:
; links. Windows does not let apps make themselves the default; the user picks it under
; Settings > Apps > Default apps (the app's "Set as Default" button opens that page).

#define AppName "Call Switcher"
#define AppExe "Call Switcher.exe"
#define ProgId "CallSwitcher.URL"

[Setup]
AppId={{B9681354-993D-40CE-A3E9-6CF56FBB42B2}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#NumericVersion}
AppPublisher=The Call Switcher contributors
AppPublisherURL=https://github.com/PhonixPBX/Call-Switcher
AppSupportURL=https://github.com/PhonixPBX/Call-Switcher/issues
AppCopyright=Copyright 2026 The Call Switcher contributors. Licensed under the Apache License 2.0.
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=CallSwitcher-{#AppVersion}-x64-setup
SetupIconFile=CallSwitcher.ico
UninstallDisplayIcon={app}\{#AppExe}
LicenseFile=..\..\LICENSE
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
; The running app (tray) is closed for updates and the uninstall.
CloseApplications=yes
ChangesAssociations=yes

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "pt"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
Source: "..\..\dist\Call Switcher\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Registry]
; The ProgID that opens the links.
Root: HKCU; Subkey: "Software\Classes\{#ProgId}"; ValueType: string; ValueData: "URL:{#AppName}"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\{#ProgId}\DefaultIcon"; ValueType: string; ValueData: """{app}\{#AppExe}"",0"
Root: HKCU; Subkey: "Software\Classes\{#ProgId}\shell\open\command"; ValueType: string; ValueData: """{app}\{#AppExe}"" ""%1"""
; Capabilities, so Call Switcher shows up under Default apps for these links.
Root: HKCU; Subkey: "Software\CallSwitcher"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\CallSwitcher\Capabilities"; ValueType: string; ValueName: "ApplicationName"; ValueData: "{#AppName}"
Root: HKCU; Subkey: "Software\CallSwitcher\Capabilities"; ValueType: string; ValueName: "ApplicationDescription"; ValueData: "Places calls from tel: links through PhonixPBX, Asterisk ARI or a phone app"
Root: HKCU; Subkey: "Software\CallSwitcher\Capabilities\URLAssociations"; ValueType: string; ValueName: "tel"; ValueData: "{#ProgId}"
Root: HKCU; Subkey: "Software\CallSwitcher\Capabilities\URLAssociations"; ValueType: string; ValueName: "callto"; ValueData: "{#ProgId}"
Root: HKCU; Subkey: "Software\CallSwitcher\Capabilities\URLAssociations"; ValueType: string; ValueName: "sip"; ValueData: "{#ProgId}"
Root: HKCU; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "{#AppName}"; ValueData: "Software\CallSwitcher\Capabilities"; Flags: uninsdeletevalue
; Written by the app ("Start at login"); only removed here.
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: none; ValueName: "{#AppName}"; Flags: dontcreatekey uninsdeletevalue

[Run]
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
