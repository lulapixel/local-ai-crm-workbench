# Entrega local da reanálise — 29/09/2026

Base: `d03b4b3001ef1788862612d79e1ad9d5499aca80`. Ordem cumprida: pesquisa primária e inspeção → plano → pesquisa complementar → patches → validação. Leia `RESEARCH-REANALYSIS.md`, `REANALYSIS-ACTION-PLAN.md` e `RESEARCH-EXPANSION.md` para fontes, escolhas e roadmap.

## Implementado

- Seleção e liberação do bot verificam telefone normalizado entre IDs, campanhas, status do CRM e sequências existentes. A checagem é repetida durante a inscrição transacional; registros não são fundidos.
- Resultado humano confirmado (`respondeu`, `fechou`, `recusou`, `ignorado`) registra evento e cancela a cadência. Pedido de não contato mantém supressão por telefone mesmo após remoção/recaptura do lead; cancela também sequências ativas/pausadas correspondentes e envios queued. Nova sequência, retomada e registro de envio da central consultam essa supressão.
- Campanhas sem saldo ou trabalho elegível não entram no snapshot estratégico. Retorno vencido e captura autorizada ainda não tentada no dia podem contar como trabalho; retorno futuro sozinho não conta.
- Painel operacional mostra próximas ações, heartbeat do processo e contagens do CRM. Relógio habilitado e execução efetiva são estados distintos; custo monetário permanece desconhecido.
- Fila com busca por nome, telefone/campanha, navegação por seções e registro de resultados, mantendo aprovação individual. Identidade mineral/turquesa e temas existentes preservados.

## Evidência

| Verificação | Resultado |
|---|---|
| Backend completo | **576 passed in 183.59s**, incluindo 15 novos casos de operações (parametrizações contam separadamente) |
| Frontend | `npm.cmd run build` e `npm.cmd run lint`: PASS; TypeScript/Vite concluídos |
| Diff | `git diff --check`: PASS; avisos de conversão LF/CRLF do Windows não são falhas |
| Browser desktop | Painel, ausência real do relógio na fixture, banner de demonstração e confirmação manual desabilitada sem checkbox verificados |
| Busca da fila | Termo sem correspondência: 0 de 1 e estado vazio; limpar: 1 de 1 |
| Browser mobile | Viewport 390×844, largura do documento 375px, sem overflow horizontal; override restaurado |
| Providers | Nenhuma chamada real de inferência, captação ou envio; rede simulada/proibida nos novos testes |

Testes rodados com Python empacotado e dependências de teste locais, `PROSPECTOS_TEST_MODE=1`, diretório de dados isolado e basetemp temporário. O comando funcional foi `python -m pytest tests -q`, com `PYTHONPATH` apontando para as dependências disponíveis. Não constitui instalação limpa ou execução de CI.

Preview em `http://127.0.0.1:5002/bot` usa base separada `.reanalysis-preview-data`, dois contatos fictícios e um cadastro duplicado. O envio exibido foi inserido diretamente como fixture; não ocorreu transmissão. Scheduler e gestão estratégica não foram ativados. Capturas desktop/mobile acompanham o pacote local de revisão.

## Limites e próximos passos

Telefone compartilhado pode bloquear outra empresa conservadoramente: resolver manualmente antes de abordar. O bloqueio implementado abrange bot e sequências da central; não impede um operador de usar aplicativos externos ou copiar um telefone. Não há desbloqueio automático. Registro humano de resposta não substitui webhook autenticado nem comprova entrega.

Requisição `sending` já iniciada pode terminar: o resultado informa essa possibilidade. Contadores representam o estado corrente do CRM, não funil histórico, causalidade ou receita. Heartbeat demonstra atividade do loop, não funcionamento de serviços externos. A leitura operacional atual varre registros para normalizar telefones; medir escala antes de introduzir índice/migração de identidade.

Não houve revisão independente, piloto comercial ou teste real de modelos. Economia, qualidade da abordagem e vantagem de multiagentes continuam não medidas. Roadmap posterior exige canais provisionados, requisitos de disponibilidade e amostras reais; essas dependências estão no plano. O usuário autorizou em 30/09/2026 a publicação dos 16 arquivos desta onda no PR público rascunho #1, sem merge ou deploy. Este relatório não comprova por si só que o push foi concluído; conferir o commit publicado no PR.
