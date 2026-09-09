# Contribuindo com o ProspectOS

Obrigado pelo interesse! Este é um projeto mantido nas horas vagas, então o
processo é leve — só bom senso.

## Antes de abrir um PR

1. **Abra uma [issue](../../issues)** descrevendo o bug ou a ideia antes de codar
   algo grande. Evita retrabalho e alinha a direção.
2. Para PRs pequenos (fix de bug, melhoria de doc), pode mandar direto.
3. Leia os avisos de risco no [README](README.md#️-antes-de-usar) — o projeto faz
   scraping e automação de conta pessoal, e isso tem implicações.

## Ambiente de desenvolvimento

Pré-requisitos: Python 3.11+, Node.js 20+, Windows (o scraper de Maps e os `.bat`
são específicos da plataforma).

```powershell
# Backend
cd backend
py -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements-lock.txt
copy .env.example .env        # preencha ao menos uma chave de IA

# Frontend
cd ../frontend
npm install
```

`requirements.txt` descreve as dependências diretas; `requirements-lock.txt`
registra as versões efetivamente validadas neste checkout. Atualize o lock
somente junto com uma nova validação da suíte.

Suba os dois de uma vez com o `iniciar.bat` na raiz. Backend em `:5000`,
frontend em `:5173`.

## Rodando os testes

```powershell
# Backend (pytest) - runtime canônico, pasta temporária isolada, timeout e
# plugins ambientais desativados por padrão
cd backend
.\run_tests.ps1

# O executor aceita argumentos adicionais do pytest, por exemplo:
.\run_tests.ps1 tests/test_url_security.py -q

# Plugins pytest instalados fora do projeto só entram com opt-in explícito:
$env:PROSPECTOS_ALLOW_AMBIENT_PYTEST_PLUGINS = '1'
.\run_tests.ps1 tests/test_url_security.py -q
Remove-Item Env:PROSPECTOS_ALLOW_AMBIENT_PYTEST_PLUGINS

# Para opções que colidem com parâmetros do PowerShell (por exemplo, -p):
.\run_tests.ps1 -TestArgs @('tests/test_url_security.py', '-p', 'no:anyio', '-q')

# Frontend (build + lint)
cd frontend
npm run build
npm run lint
```

Os testes do backend não dependem de rede, scraper ou banco real (usam SQLite
temporário e mocks dos provedores). Toda mudança de comportamento deve vir com
teste.

## Convenções de código

- **Nomes do domínio em português** (`leads`, `nichos`, `avaliar_site`,
  `gerar_mensagem`) — o vocabulário do negócio é pt-BR. Termos técnicos e libs
  ficam na forma original.
- **Backend**: Flask organizado em blueprints por domínio (`rotas_*.py`) + módulos
  dedicados (`ia.py`, `jobs.py`, `db.py`, `diagnostico.py`). Acesso ao banco sempre
  via `db.conectar()` com queries parametrizadas.
- **Frontend**: React + TypeScript. Server state com TanStack React Query; a camada
  é `services` (HTTP) → `hooks` (React Query) → `components`. Sem `any`.
- **Nunca** commite `.env`, `leads.db`, sessões do Instagram, CSVs de saída ou o
  binário do scraper — o `.gitignore` já cobre, mas confira com `git status` antes.

## Estilo de commit

Mensagens em português, no imperativo, com prefixo de tipo quando fizer sentido
(`feat:`, `fix:`, `refactor:`, `docs:`). Corpo explicando o *porquê* quando a
mudança não é óbvia.

Seja respeitoso nas discussões. É isso. 🙂
### Diagnóstico de falhas do runner

Em caso de falha ou timeout, o runner preserva os diretórios da execução em `%TEMP%\\ProspectOS-pytest` para diagnóstico; somente uma execução com exit 0 remove os diretórios que ela própria criou. Guarde o erro sanitizado antes de limpar uma pasta preservada.

Para opções curtas do pytest que possam ser interpretadas pelo PowerShell, prefira a forma posicional direta (`.\\run_tests.ps1 tests/test_url_security.py -p no:anyio -q`) ou coloque as opções com hífen antes do caminho no array nomeado (`-TestArgs @('-p', 'no:anyio', '-q', 'tests/test_url_security.py')`).

### Desktop Electron

O desktop usa `desktop/package-lock.json` como fonte única de dependências.
Em uma janela com rede ou cache npm completo, execute:

```powershell
cd desktop
# Se o cache global do Windows estiver bloqueado, mantenha os caches gerados
# dentro do desktop (todos são ignorados pelo .gitignore):
$env:NPM_CONFIG_CACHE = (Join-Path (Get-Location) '.npm-cache')
$env:ELECTRON_CACHE = (Join-Path (Get-Location) '.electron-cache')
$env:ELECTRON_BUILDER_CACHE = (Join-Path (Get-Location) '.electron-builder-cache')
npm.cmd ci --no-audit --no-fund
npm.cmd start                 # smoke local; exige o backend bundle
npm.cmd run dist -- "-c.electronDownload.cache=$(Join-Path (Get-Location) '.electron-cache')"  # sem publicar
```

Antes do smoke/empacotamento, confirme que `..\backend\dist\ProspectOS\ProspectOS.exe`
existe. O Electron pode gerar um instalador mesmo quando o `extraResources` do
backend está ausente; nesse caso o resultado é somente mecânico e o app falha
fechado com `Backend não encontrado`. O bundle deve ser produzido pelo PyInstaller
com os assets declarados (`google-maps-scraper.exe` e `node\node.exe`), nunca por
executáveis placeholder.

Em hosts com `VerifiedAndReputableDesktop`/Smart App Control, o executável
Electron sem assinatura pode ser bloqueado mesmo quando `npm.cmd run dist`
termina com exit 0. Esse bloqueio é uma política de segurança do host: não a
desative para testar. Use um certificado de assinatura aprovado ou registre a
exceção administrativa antes de declarar o smoke do instalador como PASS.

Não trate `npm ci --offline` como instalação válida quando o cache estiver
incompleto: ele pode parar em `ENOTCACHED` e deixar uma árvore parcial. Depois
de uma falha, remova apenas `desktop\\node_modules` gerado pela tentativa e
repita em uma janela controlada. Revise os avisos de dependências Git/transitivas
antes de publicar; nunca execute `npm.cmd run publicar` como teste.
