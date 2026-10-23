# Envia para o GitHub, a cada execucao, o que mudou no projeto.
# Roda pela tarefa agendada "Spectra - sincronizar GitHub" (veja o README).
$ErrorActionPreference = 'Stop'
$env:GCM_INTERACTIVE = 'never'
Set-Location (Split-Path $PSScriptRoot -Parent)

$log = Join-Path $env:TEMP 'spectra-sincronizar.log'
function Registrar($texto) { "$(Get-Date -Format s)  $texto" | Out-File $log -Append -Encoding utf8 }

try {
    $ramo = (git rev-parse --abbrev-ref HEAD).Trim()
    if (git status --porcelain) {
        git add -A
        git commit -q -m "Sincronizacao automatica $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
        Registrar "commit em $ramo"
    }
    $pendentes = git rev-list --count "origin/$ramo..HEAD" 2>$null
    if ($LASTEXITCODE -ne 0 -or [int]$pendentes -gt 0) {
        git push -q -u origin $ramo 2>&1 | Out-Null
        Registrar "push de $ramo"
    }
} catch {
    Registrar "erro: $_"
}
