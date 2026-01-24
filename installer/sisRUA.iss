[Setup]
AppName=sisRUA
AppVersion=1.0.0
AppPublisher=sisRUA
DefaultDirName={commonappdata}\Autodesk\ApplicationPlugins\sisRUA.bundle
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputBaseFilename=sisRUA-Installer
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
UninstallDisplayName=sisRUA (AutoCAD Plugin)

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
; Copia o bundle pronto (gerado por organizar_projeto.cmd)
Source: "..\release\sisRUA.bundle\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Run]
; Sem ações pós-instalação por enquanto.
; O AutoCAD carrega o bundle automaticamente via PackageContents.xml.

