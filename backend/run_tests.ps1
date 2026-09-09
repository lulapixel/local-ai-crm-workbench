[CmdletBinding(PositionalBinding = $false)]
param(
    [ValidateRange(1, 3600)]
    [int] $TimeoutSeconds = 300,

    [Parameter(Position = 0, ValueFromRemainingArguments = $true)]
    [string[]] $TestArgs = @()
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$backendRoot = [System.IO.Path]::GetFullPath($PSScriptRoot)
$pythonPath = Join-Path $backendRoot 'venv\Scripts\python.exe'

if (-not (Test-Path -LiteralPath $pythonPath -PathType Leaf)) {
    throw "Runtime canônico ausente: $pythonPath. Instale backend\\requirements.txt no venv do projeto."
}

# A pasta de temporários dentro do checkout pode ficar com ACL restritiva
# depois de uma execução interrompida. Use a área temporária do Windows para
# manter o runner executável e não poluir o source-of-truth com artefatos de
# teste. Um --basetemp explícito continua sendo respeitado; os dados do app
# continuam isolados em uma raiz temporária própria.
$tempRoot = Join-Path ([System.IO.Path]::GetTempPath()) 'ProspectOS-pytest'

$pytestInvocationArgs = @('-m', 'pytest', '-p', 'no:cacheprovider') + @($TestArgs)
$hasBasetemp = @($pytestInvocationArgs | Where-Object { $_ -eq '--basetemp' -or $_ -like '--basetemp=*' }).Count -gt 0
$runId = Get-Date -Format 'yyyyMMdd-HHmmssfff'
$testDataRoot = Join-Path $tempRoot "data-$runId"
New-Item -ItemType Directory -Path $testDataRoot -Force | Out-Null
$ownsBaseTemp = $false
if (-not $hasBasetemp) {
    $baseTemp = Join-Path $tempRoot $runId
    New-Item -ItemType Directory -Path $baseTemp -Force | Out-Null
    $ownsBaseTemp = $true
    $pytestInvocationArgs += @('--basetemp', $baseTemp)
}

$startInfo = [System.Diagnostics.ProcessStartInfo]::new()
$startInfo.FileName = $pythonPath
$startInfo.WorkingDirectory = $backendRoot
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.RedirectStandardOutput = $true
$startInfo.RedirectStandardError = $true

# Plugins de terceiros carregados automaticamente podem introduzir hooks,
# fixtures ou event loops que não pertencem ao checkout e já causaram uma
# execução MCP presa. O runner continua usando os plugins nativos do pytest;
# quem realmente precisar de plugins ambientais pode optar explicitamente com
# PROSPECTOS_ALLOW_AMBIENT_PYTEST_PLUGINS=1 no processo chamador.
$allowAmbientPlugins = $env:PROSPECTOS_ALLOW_AMBIENT_PYTEST_PLUGINS -in @('1', 'true', 'yes')
if (-not $allowAmbientPlugins) {
    $startInfo.EnvironmentVariables['PYTEST_DISABLE_PLUGIN_AUTOLOAD'] = '1'
}
$startInfo.EnvironmentVariables['PROSPECTOS_TEST_MODE'] = '1'
$startInfo.EnvironmentVariables['PROSPECTOS_TEST_DATA_DIR'] = $testDataRoot

# ArgumentList está disponível nos runtimes .NET modernos. O fallback mantém
# compatibilidade com Windows PowerShell 5.1, que é usado em algumas máquinas.
$argumentListProperty = $startInfo.PSObject.Properties['ArgumentList']
if ($null -ne $argumentListProperty) {
    foreach ($arg in $pytestInvocationArgs) {
        [void] $startInfo.ArgumentList.Add([string] $arg)
    }
} else {
    $quoted = foreach ($arg in $pytestInvocationArgs) {
        $value = ([string] $arg) -replace '"', '\"'
        '"' + $value + '"'
    }
    $startInfo.Arguments = $quoted -join ' '
}

$process = [System.Diagnostics.Process]::new()
$process.StartInfo = $startInfo
try {
    if (-not $process.Start()) {
        throw 'Não foi possível iniciar o processo do pytest.'
    }

    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    $finished = $process.WaitForExit($TimeoutSeconds * 1000)
    $timedOut = -not $finished

    if ($timedOut) {
        # Mata somente a árvore do pytest que este executor iniciou; evita
        # deixar workers órfãos quando um teste trava ou excede o limite.
        & taskkill.exe /PID $process.Id /T /F 2>$null | Out-Null
        [void] $process.WaitForExit(10000)
    }

    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()
    if ($stdout) { Write-Output $stdout.TrimEnd() }
    if ($stderr) { [Console]::Error.WriteLine($stderr.TrimEnd()) }

    if ($timedOut) {
        [Console]::Error.WriteLine("pytest excedeu o limite de $TimeoutSeconds segundos; a árvore PID $($process.Id) foi encerrada.")
        exit 124
    }

    $exitCode = $process.ExitCode
    if ($exitCode -eq 0) {
        # Só remova diretórios criados por esta execução e somente após sucesso.
        # Falhas e timeouts conservam os artefatos para diagnóstico.
        $tempRootFull = ([System.IO.Path]::GetFullPath($tempRoot)).TrimEnd('\') + '\'
        $ownedPaths = @($testDataRoot)
        if ($ownsBaseTemp) { $ownedPaths += $baseTemp }
        foreach ($ownedPath in $ownedPaths) {
            if ([string]::IsNullOrWhiteSpace([string] $ownedPath)) { continue }
            $candidateFull = [System.IO.Path]::GetFullPath([string] $ownedPath)
            if (-not $candidateFull.StartsWith($tempRootFull, [System.StringComparison]::OrdinalIgnoreCase)) {
                continue
            }
            if (Test-Path -LiteralPath $candidateFull) {
                Remove-Item -LiteralPath $candidateFull -Recurse -Force -ErrorAction SilentlyContinue
            }
        }
    }

    exit $exitCode
} finally {
    $process.Dispose()
}
