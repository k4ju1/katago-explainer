; Native KaTrain host + KataGo Explainer, installed for the current user.
; The Python builder supplies verified source paths and version definitions.
#ifndef PayloadDir
  #error "Use scripts/build_installer.py to provide the verified payload."
#endif
#ifndef AppVersion
  #error "AppVersion is required."
#endif
#ifndef AppNumericVersion
  #error "AppNumericVersion is required."
#endif
#ifndef OutputDirPath
  #error "OutputDirPath is required."
#endif
#ifndef ChineseLanguageFile
  #error "ChineseLanguageFile is required."
#endif
#ifndef ChineseConfigFile
  #error "ChineseConfigFile is required."
#endif
#ifndef EnglishConfigFile
  #error "EnglishConfigFile is required."
#endif

[Setup]
AppId={{5ED213A9-D9EC-47D8-A41C-7646A2F46843}
AppName=KataGo Explainer
AppVersion={#AppVersion}
VersionInfoVersion={#AppNumericVersion}
AppPublisher=KataGo Explainer contributors
AppPublisherURL=https://github.com/k4ju1/katago-explainer
AppSupportURL=https://github.com/k4ju1/katago-explainer/issues
DefaultDirName={localappdata}\Programs\KataGo Explainer
DefaultGroupName=KataGo Explainer
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible and not arm64
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir={#OutputDirPath}
OutputBaseFilename=KataGo-Explainer-Setup-v{#AppVersion}-win64
UninstallDisplayIcon={app}\KaTrain\KaTrain.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableWelcomePage=no
DisableProgramGroupPage=yes
CloseApplications=yes
RestartApplications=no
UsePreviousTasks=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "chinesesimplified"; MessagesFile: "{#ChineseLanguageFile}"

[CustomMessages]
english.DesktopShortcut=Create a desktop shortcut
chinesesimplified.DesktopShortcut=创建桌面快捷方式
english.LaunchApplication=Open KataGo Explainer
chinesesimplified.LaunchApplication=打开 KataGo Explainer

[Tasks]
Name: "desktopicon"; Description: "{cm:DesktopShortcut}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
; The app and its upstream notices are replaced during upgrades. User config
; is created only once, and survives both upgrades and uninstall.
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Excludes: "portable-config.json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#EnglishConfigFile}"; DestDir: "{app}"; DestName: "portable-config.json"; Flags: onlyifdoesntexist uninsneveruninstall; Check: not IsChineseSelected
Source: "{#ChineseConfigFile}"; DestDir: "{app}"; DestName: "portable-config.json"; Flags: onlyifdoesntexist uninsneveruninstall; Check: IsChineseSelected

[Icons]
Name: "{group}\KataGo Explainer"; Filename: "{app}\KaTrain\KaTrain.exe"; Parameters: """{app}\portable-config.json"""; WorkingDir: "{app}\KaTrain"
Name: "{autodesktop}\KataGo Explainer"; Filename: "{app}\KaTrain\KaTrain.exe"; Parameters: """{app}\portable-config.json"""; WorkingDir: "{app}\KaTrain"; Tasks: desktopicon

[Run]
Filename: "{app}\KaTrain\KaTrain.exe"; Parameters: """{app}\portable-config.json"" ""{app}\examples\shusaku-demo.sgf"""; WorkingDir: "{app}\KaTrain"; Description: "{cm:LaunchApplication}"; Flags: nowait postinstall skipifsilent runasoriginaluser

[Code]
function IsChineseSelected: Boolean;
begin
  Result := ActiveLanguage = 'chinesesimplified';
end;
