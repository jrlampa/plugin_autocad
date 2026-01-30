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
SetupIconFile=assets\sisrua_installer.ico
WizardImageFile=assets\wizard_large.bmp
WizardSmallImageFile=assets\wizard_small.bmp

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


procedure KillBackendProcess;
var
  ResultCode: Integer;
begin
  // Tenta matar qualquer instância do backend rodando
  Exec('taskkill', '/F /IM sisrua_backend.exe /T', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function InitializeSetup(): Boolean;
var
  answer: Integer;
  ErrorCode: Integer;
begin
  Result := True;
  
  // Mata processos antigos antes de qualquer verificação
  KillBackendProcess();

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

function TryAddTrustedPathToKey(const Key: string; const PathToTrust: string): Boolean;
var
  existing: string;
begin
  existing := '';
  RegQueryStringValue(HKCU, Key, 'TRUSTEDPATHS', existing);
  Result := not TrustedPathsContains(existing, PathToTrust);
  if Result then
  begin
    existing := AppendTrustedPath(existing, PathToTrust);
    RegWriteStringValue(HKCU, Key, 'TRUSTEDPATHS', existing);
  end;
end;

function AddTrustedPathToAllAutoCADProfiles(const PathToTrust: string): Integer;
var
  versions: TArrayOfString;
  products: TArrayOfString;
  profiles: TArrayOfString;
  v, p, pr: Integer;
  verKey, prodKey, profKey, generalKey: string;
  touched: Integer;
begin
  touched := 0;
  if not RegGetSubkeyNames(HKCU, AUTOCAD_ROOT, versions) then
  begin
    Result := 0;
    exit;
  end;

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
        if TryAddTrustedPathToKey(generalKey, PathToTrust) then
          touched := touched + 1;
      end;
    end;
  end;

  Result := touched;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  trustedUser: string;
  trustedMachine: string;
  countTouched: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Evita o aviso de segurança do AutoCAD quando a DLL é carregada a partir do Roaming (HKCU).
    // Usa a sintaxe "\..." para confiar também em subpastas.
    trustedUser := ExpandConstant('{userappdata}\Autodesk\ApplicationPlugins\sisRUA.bundle\...');
    trustedMachine := ExpandConstant('{commonappdata}\Autodesk\ApplicationPlugins\sisRUA.bundle\...');

    countTouched := 0;
    countTouched := countTouched + AddTrustedPathToAllAutoCADProfiles(trustedUser);
    countTouched := countTouched + AddTrustedPathToAllAutoCADProfiles(trustedMachine);

    // Se o AutoCAD/Civil 3D nunca foi aberto, as chaves/perfis podem não existir ainda.
    // Nesse caso, apenas orienta o usuário a configurar manualmente.
    if countTouched = 0 then
    begin
      MsgBox(
        'Aviso: nao foi possivel configurar automaticamente as pastas confiaveis do AutoCAD.'#13#10#13#10 +
        'Isso normalmente acontece quando o AutoCAD/Civil 3D ainda nao foi aberto neste usuario (perfil nao criado no registro).'#13#10#13#10 +
        'Para evitar o aviso de seguranca ("Trusted Folder"), abra o AutoCAD e adicione manualmente:'#13#10 +
        'Options > Files > Trusted Locations:'#13#10 +
        '  "' + trustedUser + '"'#13#10 +
        '  "' + trustedMachine + '"',
        mbInformation,
        MB_OK
      );
    end;
  end;
end;

