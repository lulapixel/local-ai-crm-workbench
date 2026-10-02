[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$runtimeRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'local-runtime'))
$executable = Join-Path $runtimeRoot 'ProspectOS.exe'
$receipt = Join-Path $PSScriptRoot 'local-validation/desktop-smoke.json'
if (-not (Test-Path -LiteralPath $executable -PathType Leaf)) { throw 'Prepare o runtime local primeiro.' }
if (-not (Test-Path -LiteralPath $receipt -PathType Leaf)) { throw 'Valide o aplicativo antes de instalar o atalho.' }
$validation = Get-Content -LiteralPath $receipt -Raw | ConvertFrom-Json
if (-not $validation.ready -or -not $validation.frontendLoaded) { throw 'A validação da janela local ainda não passou.' }
$desktopFolder = [Environment]::GetFolderPath('Desktop')
if (-not (Test-Path -LiteralPath $desktopFolder -PathType Container)) { throw 'Área de trabalho indisponível.' }
$shortcutPath = Join-Path $desktopFolder 'ProspectOS Local.lnk'
$shellObject = New-Object -ComObject WScript.Shell
$shortcut = $shellObject.CreateShortcut($shortcutPath)
if ((Test-Path -LiteralPath $shortcutPath) -and $shortcut.TargetPath -ne $executable) { throw 'Já existe um atalho com este nome apontando para outro aplicativo.' }
$shortcut.TargetPath = $executable
$shortcut.WorkingDirectory = $runtimeRoot
$shortcut.IconLocation = Join-Path $runtimeRoot 'resources/app/prospectos.ico'
$shortcut.Description = 'ProspectOS Local — central de operação, CRM e bot'
$shortcut.Arguments = ''
$shortcut.Save()
$checked = $shellObject.CreateShortcut($shortcutPath)
if ($checked.TargetPath -ne $executable -or $checked.Arguments -ne '') { throw 'Não foi possível validar o atalho criado.' }
[pscustomobject]@{ shortcut = $shortcutPath; executable = $checked.TargetPath; workingDirectory = $checked.WorkingDirectory } | ConvertTo-Json
