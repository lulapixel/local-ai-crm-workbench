# Validação da mesa do gestor e do workspace local

Data: 2026-10-02. Resultados de execução local, não resultados de CI nem validação comercial. O pacote reúne a mesa do gestor e suas dependências da fila operacional, pesquisa local e launcher desktop.

## Verificações executadas

| Verificação | Resultado |
| --- | --- |
| Backend completo, dados isolados | 661 testes passaram em 160,95 s |
| Recorte de gestão, fila, pesquisa e estratégia | 92 testes passaram em 81,13 s; subconjunto da regressão |
| Frontend: estratégia, pesquisa e gestão | 9 testes passaram |
| Runtime do launcher | 7 testes passaram |
| TypeScript, oxlint e build Vite final | Passaram; build final em 3,93 s |
| Navegador: desktop / tablet / celular | Larguras verificadas de 1280 / 900 / 390 px, sem overflow horizontal |
| Inicialização desktop com base de teste | Serviço pronto e rota inicial `/` carregada, com automação desativada |

O smoke nativo falhou ao iniciar o renderer no ambiente restrito. A repetição fora desse ambiente carregou a rota inicial mantendo sandbox e isolamento de contexto do Electron. A captura nativa opcional retornou `UnknownVizError`; não é evidência visual. A conferência visual foi realizada separadamente no navegador, em temas claro e escuro. O smoke nativo não cobre toda a operação do aplicativo.

## Cenários funcionais

- Oferta fictícia: salvamento de público, resultado, escopo, preço, prazo e demonstração; progressão do checklist somente com requisitos e revisões explícitos.
- Alterações relevantes invalidam revisões anteriores da oferta. URL de demonstração rejeita esquemas executáveis, credenciais e caminhos não permitidos; não é buscada pelo backend.
- Duas janelas: a gravação antiga recebe 409, preserva o rascunho e oferece descarte explícito para carregar a versão atual. Refetch e mudança de mês não apagam edições.
- Recebimento fictício e anulação: resumo mensal atualizado, registro anulado preservado. Testes cobrem centavos exatos, idempotência, data futura e totais acima do recorte de 30 registros.
- Preferência de cidade apenas desempata ações com a mesma prioridade e vencimento; respostas e retornos urgentes não são deslocados pelo perfil.
- Requisições de navegador sem token CSRF e com origem externa foram recusadas com 403. Leitura de gestão retornou `Cache-Control: no-store`. Clientes CLI/MCP sem sinais de navegador seguem a política local existente; esse teste não equivale a autenticação multiusuário.
- Navegação por teclado e foco visível conferidos. A versão final com dados locais não apresentou erros ou avisos no console durante a observação.

## Reprodução

Use Python com as dependências do backend e Node com as dependências do frontend já instaladas. Não execute testes contra a base pessoal. Em PowerShell, defina `PROSPECTOS_TEST_MODE=1`, `PROSPECTOS_TEST_DATA_DIR` com um diretório absoluto exclusivo para testes, `PROSPECTOS_AUTOMATION_DISABLED=1`, `PROSPECTOS_BOT_LIVE_SENDS=0` e `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`.

- Em `backend`: `python -m pytest -q -p no:cacheprovider`.
- Em `frontend`: `node --test tests/*.test.mjs`, `npm.cmd run lint` e `npm.cmd run build` (inclui TypeScript).
- Na raiz: `node --test desktop/tests/*.test.js`.
- Com runtime desktop preparado: `ProspectOS.exe --smoke`. O recibo fica em `desktop/local-validation/desktop-smoke.json`.

## Dados, alcance e limites

O repositório contém código, testes com exemplos fictícios e documentação. Banco do CRM, credenciais, perfil pessoal completo, relatórios privados, capturas com dados locais, runtimes e dependências ficam fora da publicação. A aplicação de preferências locais criou backup e verificou que o conteúdo das tabelas anteriores permaneceu igual.

Nenhuma inferência real, captura externa ou transmissão foi executada nesta validação. O contexto estratégico foi testado como estrutura limitada, sem meta financeira ou recebimentos. Perfil e prontidão não concedem novas permissões ao bot. Economia, conversão, receita e vantagem de multiagentes permanecem não medidas. Não houve revisão humana de aceitação nem revisão independente desta entrega. A publicação permanece no PR rascunho, sem merge ou deploy.
