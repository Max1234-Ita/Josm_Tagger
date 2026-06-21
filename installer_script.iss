; Script di esempio per Inno Setup
[Setup]
AppName=Josm Tagger
AppVersion=1.0
DefaultDirName={autopf}\JosmTagger
DefaultGroupName=Josm Tagger
UninstallDisplayIcon={app}\main.exe
Compression=lzma2
SolidCompression=yes
OutputDir=D:\Sviluppo\PythonProject\Josm_Tagger\dist_installer
OutputBaseFilename=JosmTagger_Setup

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Assumi che la tua cartella dist di PyInstaller contenga l'eseguibile e le dipendenze
Source: "D:\Sviluppo\PythonProject\Josm_Tagger\dist\main\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Includi esplicitamente il file di configurazione se non è già nella dist
Source: "D:\Sviluppo\PythonProject\Josm_Tagger\config.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Josm Tagger"; Filename: "{app}\main.exe"
Name: "{autodesktop}\Josm Tagger"; Filename: "{app}\main.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\main.exe"; Description: "{cm:LaunchProgram,Josm Tagger}"; Flags: nowait postinstall skipifsilent

[Code]
// Puoi aggiungere logica Pascal qui per controllare pre-requisiti o configurazioni particolari
function InitializeSetup(): Boolean;
begin
  Result := True;
end;