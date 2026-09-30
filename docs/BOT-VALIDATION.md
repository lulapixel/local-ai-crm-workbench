# Validação local do bot — 2026-09-30 UTC

Estado no momento da validação: implementado e validado localmente, antes do commit/publicação no PR público #1. Base Git: `0ff40aab8abba332d8a1702105b678444e38a98d`. O registro posterior de publicação está na entrega ao usuário.

## Evidência confirmada

- Backend: `pytest tests -q`, **561 passed in 158.26s**. Inclui contratos do bot, aprovação, contato alterado, deduplicação com a central, limites antes de enriquecimento externo, pausa, recuperação, cinco combinações de modelo/esforço, agenda, teto de tentativas, dupla, relato divergente, feedback e conectores simulados.
- Frontend: `npm run build` e `npm run lint`, ambos concluídos com código 0; TypeScript e Vite passaram.
- `git diff --check` passou para os arquivos rastreados. Artefatos de entrega usam lista explícita de código/documentação; dados, dependências, credenciais e pastas temporárias não entram no pacote.
- Browser: campanha sintética com dois leads, ensaio, preparação, aprovação de texto e prévia de e-mail `lead@example.test`. Cinco combinações e cinco tipos de chamada (incluindo automático) visíveis; agenda salva somente na base isolada de demonstração. Registro manual exige confirmação. Serviço ausente bloqueia envio automático.
- Layout desktop e mobile de 390px inspecionados; largura do documento de 390px, sem transbordamento horizontal nessa verificação. Screenshots: `bot-management-desktop.jpg` e `bot-management-mobile.jpg`, na pasta de entrega.
- Codex CLI instalado e comandos/opções consultados. Consulta de autenticação no usuário normal confirmou sessão ChatGPT, sem ler tokens nem executar inferência. Sob o usuário isolado do sandbox, a autenticação não foi confirmada.

## Limites da evidência

Nenhuma chamada real de modelo, captura externa ou mensagem real foi executada nesta validação. Invocação do CLI, pin relatado e restrições de ferramentas foram testados com mocks; a primeira chamada autorizada na janela ainda precisa confirmar comportamento real. Uma divergência ou relato ausente bloqueia o plano. O relato do CLI não prova independentemente o modelo servido.

A prévia em `127.0.0.1:5001/bot` usa dados sintéticos e importação do app sem scheduler. A execução normal de `backend/app.py` inicia o relógio; o operador deve habilitar a gestão no banco real. Janela de 15h00–15h09 Brasília, uma rodada/dia, até duas invocações incluindo falhas; backend aberto necessário. Não foi testada execução futura nem reinício real do processo durante transmissão.

WhatsApp Cloud API e Resend têm adaptadores preparados e testes simulados; faltam contas, credenciais locais, template/remetente e teste de entrega. Envios permanecem desativados. Aceitação do provedor é distinta de entrega/leitura. Webhooks de resposta, entrega e unsubscribe não estão implementados. O status atualizado no CRM interrompe a cadência.

Aprendizado significa reutilizar resultados agregados e avaliação humana na próxima análise. Não há autoalteração de código ou permissões. Paperclip não instalado; funções locais não são múltiplos agentes LLM. Dupla usa duas sessões correlacionadas, não revisão humana independente.

Qualidade comparativa, custo monetário, latência real de inferência, conversão e superioridade do SOL seguem **não medidos**. Política SOL-OPS-1 é heurística versionada. Registros SOL desta expansão são descritivos: alguns pedidos foram capturados após a implementação, sem retrodatação, nova unidade independente ou selo M2.

## Próxima ativação

Revisar e habilitar campanhas reais na aplicação normal; acompanhar uma primeira chamada às 15h Brasília. Provisionar canais separadamente e verificar um envio aprovado antes de operação comercial. Publicação desta expansão requer autorização para atualizar o PR público #1; nenhum merge ou deploy faz parte da entrega local.
