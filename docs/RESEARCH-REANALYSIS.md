# Reanálise do workbench — 29/09/2026, horário do usuário

Base inspecionada: `d03b4b3001ef1788862612d79e1ad9d5499aca80`. Método: leitura de módulos, contratos, testes e interface; pesquisa de documentação primária; comparação de alternativas antes de implementação. Não é auditoria exaustiva de segurança nem pesquisa de mercado com clientes. Evidência local, documentação externa, hipótese de produto e validação comercial são categorias distintas.

## Diagnóstico por dimensão

| Dimensão | Evidência no projeto | Consequência e direção |
|---|---|---|
| Identidade dos contatos | `bot_targets` é único por place_id; `_disponiveis` não elimina telefones iguais | Dois IDs podem atingir a mesma pessoa. Normalizar contato e conferir novamente dentro da transação de inscrição e antes da liberação. Não unir empresas automaticamente. |
| Recusa e resposta | Bot reage a status do CRM, mas sua página não oferece registro direto de resposta nem supressão persistente por contato | Fechar o ciclo manualmente, registrar resposta e cancelar cadência; bloqueio durável deve resistir à recaptura com outro ID. |
| Automação | Scheduler em thread, recuperação conservadora no startup, orçamento de chamadas transacional | Adequado à operação local pequena. Expor heartbeat real; não aparentar execução contínua quando o backend não iniciou o relógio. |
| Economia de inferência | Snapshot inclui qualquer campanha idle, mesmo sem saldo, leads ou retorno vencido | Filtrar trabalho útil antes da chamada. Cota de assinatura não é custo monetário medido. |
| Design | Identidade azul mineral/turquesa consistente; página do bot extensa e configuração precede a fila humana | Abrir com situação da operação e próximo passo; navegação por âncoras, fila pesquisável e agenda visível. Manter identidade; reduzir ornamento que não informa estado. |
| Praticidade | Aprovação, abertura de WhatsApp e confirmação manual são distintas; preparo pode ser ensaiado | Preservar revisão individual. Acrescentar ações de resultado, atalhos para seções e lista de contatos em acompanhamento. |
| Qualificação | Score determinístico mistura oportunidade do site, nota e avaliações; não mede intenção de compra | Mostrar score como oportunidade, não probabilidade de conversão. Futuro: separar adequação, engajamento e qualidade dos dados. |
| Integração | Flask/SQLite/React, MCP existente, Resend/Meta preparados; canais sem contas | Manter adaptadores pequenos. Não instalar n8n, Paperclip ou servidor de workflow somente para ganhar nomes novos. |
| Confiabilidade | SQL usa WAL e busy_timeout; outbox distingue aceitação de resultado incerto | Persistência e idempotência já ajudam. Falta reconciliação com provedor e recebimento de eventos autenticados. Não repetir envio incerto. |
| Observabilidade | Histórico existe, mas poucas informações sobre gargalo e relógio são acionáveis | Agregar fila, pendências, respostas e estado do scheduler; custo desconhecido deve permanecer desconhecido. |
| Segurança e privacidade | Proteções locais de origem/CSRF e contratos limitados; modelo não recebe telefones por desenho | Preservar controle determinístico. Dados de campanha ainda são entrada não confiável; restrições do CLI exigem confirmação real. Supressão ajuda operação, não certifica conformidade jurídica. |
| Complexidade/manutenção | Três módulos de bot mais política; CSS e JSX comprimidos; sem workflow `.github` | Componentes adicionais pequenos; evitar novo framework e serviço. Separar estado operacional e resultados num módulo coeso; documentar contratos. CI e formatação sistemática são próximos passos, não justificam migrar stack. |
| Operação comercial | Conversão real e economia não medidas; usuário ainda não recebeu por trabalho de tecnologia | Priorizar fluxo demonstrável para primeiro cliente e registro de respostas. Automatizar volume sem validar oferta pode ampliar desperdício. |
| SOL/experimentos | Heurísticas e feedback, sem grupos comparáveis e inferência real verificada | Instrumentar trabalho útil, abstenção e resultado, depois piloto preregistrado. Dupla não é automaticamente superior a solo. |

## Pesquisa primária e adaptação

1. [Paperclip — conceitos](https://docs.paperclip.ing/guides/welcome/key-concepts/): separa agentes, tarefas, orçamento e aprovações, com propriedade exclusiva de trabalho. Aplicação aqui: fila e responsabilidades claras; estrutura de empresa completa é desproporcional ao volume atual.
2. [n8n — revisão humana](https://docs.n8n.io/advanced-ai/human-in-the-loop-tools): revisão sobre uma ação concreta antes da execução. Manter autorização específica por mensagem; evitar aprovar um lote de destinatários sem revisão individual.
3. [Temporal — atividades](https://docs.temporal.io/activity-definition): efeitos externos e repetição precisam de idempotência. A decisão local é preservar outbox e estado incerto; considerar engine durável apenas quando houver execução contínua e volume que justifiquem sua operação.
4. [SQLite — WAL](https://sqlite.org/wal.html): leitores e um escritor podem operar com concorrência, mas WAL não transforma SQLite em múltiplos escritores. Transações curtas; nenhuma chamada de rede dentro da transação de gravação.
5. [Resend — idempotência](https://resend.com/docs/dashboard/emails/idempotency-keys): retenção da chave por 24 horas. Nosso bloqueio local de estado incerto não pode depender de deduplicação eterna do provedor.
6. [Resend — webhooks](https://resend.com/docs/webhooks/introduction): eventos de entrega e bounce e verificação de autenticidade. Próxima integração exige endpoint HTTPS, credencial e prevenção de replay; localhost não recebe eventos públicos por si só.
7. [HubSpot — scoring](https://knowledge.hubspot.com/scoring/understand-the-lead-scoring-tool): distingue adequação e engajamento. Usar essa separação como hipótese de evolução; não atribuir intenção com base em ausência de site.
8. [Google Places — Text Search](https://developers.google.com/maps/documentation/places/web-service/text-search) e [campos/SKU](https://developers.google.com/maps/documentation/places/web-service/data-fields): field mask explícito e tier dos campos influenciam requisição/cobrança. O código já tem máscara explícita, incluindo telefone/site. Não remover esses campos sem preservar o fluxo de qualificação. Futuro: medir busca ID-only + enriquecimento seletivo contra máscara atual.
9. [OpenTelemetry — observabilidade](https://opentelemetry.io/docs/concepts/observability-primer/): métricas, eventos e correlação ajudam a explicar falhas. Aplicação local: contadores e heartbeat sem exportar leads; exporter externo só se necessário.
10. [OWASP — agência excessiva](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) e [segurança de agentes](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html): ferramentas e permissões mínimas, aprovação para efeitos relevantes. Manter modelo planejador sem autorizar envio, código ou aumento de limites.
11. [W3C — WCAG 2.2](https://www.w3.org/TR/WCAG22/) e [alvos de interação](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html): reflow, foco e mensagens de estado orientam UI. Verificar mobile e teclado; uma inspeção local não certifica toda a aplicação.
12. [GitHub — uso seguro de Actions](https://docs.github.com/en/actions/reference/security/secure-use): permissões mínimas e controle de dependências de workflow. Planejar CI sem segredos de CRM/provedor, com dados temporários e rede simulada.
13. [ANPD — orientação sobre legítimo interesse](https://www.gov.br/anpd/pt-br/assuntos/noticias/anpd-lanca-guia-orientativo-sobre-legitimo-interesse): a orientação trata finalidade, necessidade, balanceamento e salvaguardas. O software deve registrar preferências e minimizar dados; não presume que contato público autoriza qualquer abordagem. A avaliação jurídica da operação é distinta de seu teste técnico.

## Alternativas e horizontes

- **Manter núcleo local:** nenhuma nova dependência de serviço, preserva ferramentas existentes; não promete disponibilidade com notebook fechado.
- **n8n como camada de integração:** útil quando há três ou mais canais provisionados e eventos reais; acrescenta configuração e dados circulando por outro runtime.
- **Paperclip como organização:** útil quando funções têm ferramentas, tarefas e orçamento realmente distintos. Hoje um gestor e revisão seletiva são suficientes para testar a hipótese sem seis inferências rotineiras.
- **Temporal/serviço durável:** útil para tarefas longas, workers distribuídos e SLA contínuo; excessivo antes de um cliente real e canal validado.
- **CRM externo como destino:** sincronização seletiva/exportação futura, mantendo CRM local como fonte até migração explicitamente escolhida. Duplicar gravações sem contrato produz divergência.
- **RAG, vetores e memória de vendas:** considerar somente com material próprio suficiente e consentido. Guardar contexto comercial útil pode melhorar preparação; ingestão irrestrita do histórico aumenta custo e exposição.
- **Experimentos de oferta e vertical:** comparar poucas ofertas claras por nicho, registrar propostas/respostas e tempo humano. Não automatizar promessas de retorno nem otimizar por volume de mensagens.

Prioridade inferida: segurança do contato + redução de chamadas vazias + operação compreensível. Economia, conversão e impacto comercial são hipóteses a medir, não resultados desta pesquisa.
