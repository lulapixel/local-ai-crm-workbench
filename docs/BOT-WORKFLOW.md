# Bot de prospecção local

## Contrato desta expansão

O bot deve selecionar oportunidades reais, preparar mensagens e follow-ups, captar quando autorizado e necessário, e oferecer uma fila humana de revisão. A stack permanece Flask/SQLite/React. Mensagens são aprovadas individualmente; abrir o WhatsApp não equivale a enviar. Registro manual exige confirmação humana explícita. A expansão estratégica usa o Codex local às 15h Brasília, com até duas chamadas/dia e escolhas limitadas de modelo/esforço. Conectores de envio automático após aprovação estão preparados, mas dependem de contas ainda não provisionadas. A automação funciona enquanto o backend estiver aberto.

Direção de produto: base antes de captura, preparação determinística sem inferência adicional, decisão estratégica seletiva, limites pequenos, ensaio antes da execução, histórico persistente, pausa e recuperação após interrupção. Leads respondidos, fechados, ignorados ou já envolvidos em uma sequência não entram novamente. Durante desenvolvimento, chamadas e envios são simulados; nenhuma mensagem real é transmitida. O estado da autenticação local foi consultado sem iniciar inferência.

Critérios de conclusão: API e painel operacionais; ensaio sem efeitos; persistência, deduplicação entre campanhas, limites, autorização de captura, pausa, aprovações invalidadas por edição ou mudança do contato, confirmação manual e follow-ups testados; lint/build e revisão visual local. Economia monetária e conversão seguem sem medição.

## Pesquisa e decisões

- [n8n — aprovação de ferramentas](https://docs.n8n.io/advanced-ai/human-in-the-loop-tools/): inspirou a revisão do texto e destinatário específicos antes de liberar uma ação.
- [HubSpot — reentrada em workflows](https://knowledge.hubspot.com/workflows/add-re-enrollment-triggers-to-a-workflow): inspirou o controle explícito de reentrada para evitar contatos repetidos.

Esses padrões foram adaptados à aplicação local. Nenhum serviço ou assinatura adicional é necessário para preparar a fila. A fonte de captura existente pode consumir recursos externos; o limite de consultas não representa um teto financeiro. A gestão estratégica consome a cota da sessão Codex. Consulte [padrão de decisão](BOT-DECISION-STANDARD.md) e [canais](BOT-CHANNELS.md) para autorizações e limites; WhatsApp oficial e e-mail exigem configuração futura, e webhooks de respostas não estão implementados.
