#ifndef AppVersion
  #define AppVersion GetEnv('SISRUA_VERSION')
#endif
#if AppVersion == ""
  #define AppVersion "0.0.0"
#endif

[Setup]
AppName=sisRUA
AppVersion={#AppVersion}
AppPublisher=sisRUA
DefaultDirName={commonappdata}\Autodesk\ApplicationPlugins\sisRUA.bundle
DisableDirPage=yes
DisableProgramGroupPage=yes
OutputBaseFilename=sisRUA-Installer-{#AppVersion}
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=admin
UninstallDisplayName=sisRUA (AutoCAD Plugin)
VersionInfoVersion={#AppVersion}

[Languages]
Name: "ptbr"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"

[Files]
; Copia o bundle pronto (gerado por organizar_projeto.cmd)
Source: "..\release\sisRUA.bundle\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Run]
; Sem ações pós-instalação por enquanto.
; O AutoCAD carrega o bundle automaticamente via PackageContents.xml.

[Code]
const
  WEBVIEW2_GUID = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWebView2Runtime(): Boolean;
var
  pv: string;
begin
  pv := '';

  Result :=
    (RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WEBVIEW2_GUID, 'pv', pv) and (pv <> '') and (pv <> '0.0.0.0')) or
    (RegQueryStringValue(HKLM, 'SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\' + WEBVIEW2_GUID, 'pv', pv) and (pv <> '') and (pv <> '0.0.0.0')) or
    (RegQueryStringValue(HKCU, 'SOFTWARE\Microsoft\EdgeUpdate\Clients\' + WEBVIEW2_GUID, 'pv', pv) and (pv <> '') and (pv <> '0.0.0.0'));
end;

function InitializeSetup(): Boolean;
var
  answer: Integer;
  ErrorCode: Integer;
begin
  Result := True;

  if not HasWebView2Runtime() then
  begin
    answer := MsgBox(
      'O sisRUA precisa do Microsoft Edge WebView2 Runtime (Evergreen) para abrir a interface.'#13#10#13#10 +
      'Clique em "Sim" para abrir o instalador oficial do WebView2 no navegador e depois rode este instalador novamente.'#13#10#13#10 +
      'Link: https://go.microsoft.com/fwlink/?LinkId=2124703',
      mbError,
      MB_YESNO
    );

    if answer = IDYES then
    begin
      ShellExec('open', 'https://go.microsoft.com/fwlink/?LinkId=2124703', '', '', SW_SHOWNORMAL, ewNoWait, ErrorCode);
    end;

    Result := False;
  end;
end;

