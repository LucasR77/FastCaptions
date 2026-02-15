; Script de Inno Setup para FastCaptions
; Descarga Inno Setup en https://jrsoftware.org/isdl.php para usar este archivo

[Setup]
AppId={{5A23B9E1-F8D2-4C9A-B3E4-91D0F8A5E2B0}
AppName=FastCaptions
AppVersion=1.0
AppPublisher=Lucas
DefaultDirName={autopf}\FastCaptions
DefaultGroupName=FastCaptions
OutputDir=release
OutputBaseFilename=FastCaptions_Setup
SetupIconFile=d:\subtitulador\app_icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Aquí asumimos que ya corriste: pyinstaller FastCaptions.spec (o subtitulador.spec modificado)
Source: "d:\subtitulador\dist\FastCaptions\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Imagen del icono para ser usada localmente si es necesario
Source: "d:\subtitulador\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\FastCaptions"; Filename: "{app}\FastCaptions.exe"; IconFilename: "{app}\app_icon.ico"
Name: "{autodesktop}\FastCaptions"; Filename: "{app}\FastCaptions.exe"; Tasks: desktopicon; IconFilename: "{app}\app_icon.ico"

[Run]
Filename: "{app}\FastCaptions.exe"; Description: "{cm:LaunchProgram,FastCaptions}"; Flags: nowait postinstall skipifsilent
