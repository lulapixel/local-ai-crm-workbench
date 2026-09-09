param(
    [Parameter(Mandatory = $true)]
    [string]$Uri,
    [ValidateRange(1, 300)]
    [int]$TimeoutSec = 20,
    [ValidateRange(50, 5000)]
    [int]$IntervalMs = 250
)

$alvo = $null
try {
    $alvo = [Uri]$Uri
} catch {
    exit 2
}

if ($alvo.Scheme -notin @("http", "https")) {
    exit 2
}

if ($alvo.Host -notin @("127.0.0.1", "localhost", "::1")) {
    exit 2
}

$limite = [DateTime]::UtcNow.AddSeconds($TimeoutSec)
while ([DateTime]::UtcNow -lt $limite) {
    try {
        $resposta = Invoke-WebRequest -Uri $alvo.AbsoluteUri -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($resposta.StatusCode -ge 200 -and $resposta.StatusCode -lt 400) {
            exit 0
        }
    } catch {
        # O processo pode ainda estar subindo; o timeout externo decide.
    }
    Start-Sleep -Milliseconds $IntervalMs
}

exit 1
