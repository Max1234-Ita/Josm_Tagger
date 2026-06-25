; Build script for Inno Setup
; --> https://jrsoftware.org/isdl.php/Inno-Setup-Downloads
;
; This script is designed to create an installer for the Josm Tagger application and meant to be run after building
; JOSM_Tagger.exe with PyInstaller.
; PyInstaller will place the executable and all its dependencies in the 'dist' folder, which is then used by this
; script to create the installer.
; The Inno Setup compiler is called from inside build_win_installer.py, which in turn is called from build.py,
; the main entry point for building the application executable.

[Setup]
AppName=Josm Tagger
AppVersion={#AppVersion}
DefaultDirName={autopf}\JosmTagger
DefaultGroupName=Josm Tagger
UninstallDisplayIcon={app}\JOSM_Tagger.exe
Compression=lzma2
SolidCompression=yes
OutputDir=D:\Sviluppo\PythonProject\Josm_Tagger\dist_installer
OutputBaseFilename=JosmTagger_Setup

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Assuming that the PyInstaller's 'dist' folder contains the executable and all the dipendencies
; Please update the path below accordingly
Source: "D:\Sviluppo\PythonProject\Josm_Tagger\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Include configuration file if not already in the dist directory
Source: "D:\Sviluppo\PythonProject\Josm_Tagger\config.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Josm Tagger"; Filename: "{app}\JOSM_Tagger.exe"
Name: "{autodesktop}\Josm Tagger"; Filename: "{app}\JOSM_Tagger.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\JOSM_Tagger.exe"; Description: "{cm:LaunchProgram,Josm Tagger}"; Flags: nowait postinstall skipifsilent

[Code]
// Add here the Pascal logic to check pre-requisites or particular configurations
function InitializeSetup(): Boolean;
begin
  Result := True;
end;


