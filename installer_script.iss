; Script de Inno Setup para Subtitulador Pro
; Descarga Inno Setup en https://jrsoftware.org/isdl.php para usar este archivo

[Setup]
AppId={{C1234567-89AB-CDEF-0123-456789ABCDEF}
AppName=Subtitulador Pro
AppVersion=3.5
AppPublisher=Lorenzo
DefaultDirName={autopf}\SubtituladorPro
DefaultGroupName=Subtitulador Pro
OutputDir=dist
OutputBaseFilename=Subtitulador_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Aquí asumimos que ya corriste: pyinstaller subtitulador.spec
Source: "d:\subtitulador\dist\subtitulador_app\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTA: Si los binarios de FFmpeg no terminaron en la carpeta dist, agrégalos manualmente aquí:
; Source: "d:\subtitulador\ffmpeg.exe"; DestDir: "{app}"; Flags: ignoreversion
; Source: "d:\subtitulador\ffprobe.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Subtitulador Pro"; Filename: "{app}\subtitulador.exe"
Name: "{autodesktop}\Subtitulador Pro"; Filename: "{app}\subtitulador.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\subtitulador.exe"; Description: "{cm:LaunchProgram,Subtitulador Pro}"; Flags: nowait postinstall skipifsilent
