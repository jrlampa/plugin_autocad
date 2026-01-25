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
; Fallback (Civil 3D/AutoCAD): também instala no ApplicationPlugins do usuário (Roaming)
; Em alguns ambientes o Autoloader pode enxergar primeiro o caminho do usuário.
Source: "..\release\sisRUA.bundle\*"; DestDir: "{userappdata}\Autodesk\ApplicationPlugins\sisRUA.bundle"; Flags: recursesubdirs createallsubdirs ignoreversion

[Run]
; Sem ações pós-instalação por enquanto.
; O AutoCAD carrega o bundle automaticamente via PackageContents.xml.

[Code]
const
  WEBVIEW2_GUID = '{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';
  AUTOCAD_ROOT = 'Software\Autodesk\AutoCAD';

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

function NormalizeTrustedPath(const P: string): string;
begin
  Result := Lowercase(Trim(P));
end;

function TrustedPathsContains(const Existing: string; const P: string): Boolean;
var
  e: string;
  p2: string;
begin
  e := NormalizeTrustedPath(Existing);
  p2 := NormalizeTrustedPath(P);
  Result := (p2 <> '') and (Pos(p2, e) > 0);
end;

function AppendTrustedPath(const Existing: string; const P: string): string;
var
  s: string;
begin
  s := Trim(Existing);
  if s <> '' then
  begin
    if Copy(s, Length(s), 1) <> ';' then
      s := s + ';';
  end;
  s := s + '"' + P + '"';
  Result := s;
end;

procedure TryAddTrustedPathToKey(const Key: string; const PathToTrust: string);
var
  existing: string;
begin
  existing := '';
  RegQueryStringValue(HKCU, Key, 'TRUSTEDPATHS', existing);
  if not TrustedPathsContains(existing, PathToTrust) then
  begin
    existing := AppendTrustedPath(existing, PathToTrust);
    RegWriteStringValue(HKCU, Key, 'TRUSTEDPATHS', existing);
  end;
end;

procedure AddTrustedPathToAllAutoCADProfiles(const PathToTrust: string);
var
  versions: TArrayOfString;
  products: TArrayOfString;
  profiles: TArrayOfString;
  v, p, pr: Integer;
  verKey, prodKey, profKey, generalKey: string;
begin
  if not RegGetSubkeyNames(HKCU, AUTOCAD_ROOT, versions) then
    exit;

  for v := 0 to GetArrayLength(versions) - 1 do
  begin
    verKey := AUTOCAD_ROOT + '\' + versions[v];
    if not RegGetSubkeyNames(HKCU, verKey, products) then
      continue;

    for p := 0 to GetArrayLength(products) - 1 do
    begin
      prodKey := verKey + '\' + products[p] + '\Profiles';
      if not RegGetSubkeyNames(HKCU, prodKey, profiles) then
        continue;

      for pr := 0 to GetArrayLength(profiles) - 1 do
      begin
        profKey := prodKey + '\' + profiles[pr];
        generalKey := profKey + '\General';
        TryAddTrustedPathToKey(generalKey, PathToTrust);
      end;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  trusted: string;
begin
  if CurStep = ssPostInstall then
  begin
    // Evita o aviso de segurança do AutoCAD quando a DLL é carregada a partir do Roaming (HKCU).
    // Usa a sintaxe "\..." para confiar também em subpastas.
    trusted := ExpandConstant('{userappdata}\Autodesk\ApplicationPlugins\sisRUA.bundle\...');
    AddTrustedPathToAllAutoCADProfiles(trusted);
  end;
end;

