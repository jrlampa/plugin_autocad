
$PipeName = "sisrua_backend"
$Timeout = 5000

Write-Host "Tentando conectar ao Named Pipe: \\.\pipe\$PipeName"

try {
  $client = New-Object System.IO.Pipes.NamedPipeClientStream(".", $PipeName, [System.IO.Pipes.PipeDirection]::InOut)
  $client.Connect($Timeout)
  Write-Host "Conectado com sucesso!"

  $msg = [System.Text.Encoding]::UTF8.GetBytes("GET_TOKEN")
  $client.Write($msg, 0, $msg.Length)
  Write-Host "Solicitacao GET_TOKEN enviada."

  $buffer = New-Object byte[] 4096
  $bytesRead = $client.Read($buffer, 0, $buffer.Length)
  $token = [System.Text.Encoding]::UTF8.GetString($buffer, 0, $bytesRead)

  Write-Host "Token Recebido: $token"
  $client.Close()
}
catch {
  Write-Host "Erro ao conectar ou ler do Pipe: $_"
}
