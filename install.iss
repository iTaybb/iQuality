#define MyAppName "iQuality"
#define MyAppVersion "0.212"  ; auto-generated
#define MyAppPublisher "Itay Brandes"
#define MyAppURL "http://iQuality.iTayb.net"
#define MyAppExeName "iQuality.exe"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
; (To generate a new GUID, click Tools | Generate GUID inside the IDE.)
AppId={{218B1FC3-5CE1-45B3-82C1-5C7390EFE744}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
;AppVerName={#MyAppName} {#MyAppVersion}                                                    
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}                                      
AppUpdatesURL={#MyAppURL}
DefaultDirName={pf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=C:\Scripts\iQuality\agreement.txt
InfoAfterFile=C:\Scripts\iQuality\README.md
OutputDir=C:\scripts\iQuality\dist
OutputBaseFilename={#MyAppName}-{#MyAppVersion}-installer
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma
SolidCompression=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "hebrew"; MessagesFile: "compiler:Languages\Hebrew.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Dirs]  
Name: "{app}"; Permissions: users-modify;

[Files]
Source: "C:\Scripts\iQuality\dist\iQuality-{#MyAppVersion}.win32\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs
Source: "C:\Scripts\iQuality\agreement.txt"; DestDir: "{app}";
Source: "C:\Scripts\iQuality\ChangeLog.txt"; DestDir: "{app}";
Source: "C:\Scripts\iQuality\README.md"; DestDir: "{app}"; DestName: README.txt;

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\ID3 Tagger"; Filename: "{app}\{#MyAppExeName}"; Parameters: "/id3"; IconFilename: "{app}\pics\id3edit.ico"
Name: "{group}\Uninstall"; Filename: "{uninstallexe}"
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall runascurrentuser skipifsilent

; Up to version v0.191, the program folder structer was kinda different.
; If we already have an older version installed, we need to move and remove
; some files to make it work with the new struct.
[Code]
function IsOldVersion: Boolean;
begin
  Result := FileExists(ExpandConstant('{app}\PyQt4.QtCore.pyd'));
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
	NeedsRestart := False;
	
	if IsOldVersion then begin
		if not DirExists(ExpandConstant('{userappdata}\iQuality')) then begin
			CreateDir(ExpandConstant('{userappdata}\iQuality'))
		end;
		
		FileCopy(ExpandConstant('{app}\config.ini'),ExpandConstant('{userappdata}\iQuality\config.ini'), True);
		FileCopy(ExpandConstant('{app}\debug.log'),ExpandConstant('{userappdata}\iQuality\debug.log'), True);
		FileCopy(ExpandConstant('{app}\debug.calcScore.log'),ExpandConstant('{userappdata}\iQuality\debug.calcScore.log'), True);
		
		DelTree(ExpandConstant('{app}'), False, True, True);
	end;
	
end;