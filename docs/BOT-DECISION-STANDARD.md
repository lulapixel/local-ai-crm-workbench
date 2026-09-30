# SOL-OPS-1 — padrão de decisão do bot

Objetivo: minimizar trabalho repetido e recursos por resultado aceito, preservando controle humano sobre contato externo e mudanças de autoridade. As regras abaixo são heurísticas explícitas, ainda sem validação comparativa de qualidade, custo ou conversão.

| Escolha | Aplicação automática inicial |
|---|---|
| Luna 6 / high | Triagem delimitada; padrão de menor esforço autorizado |
| Luna 6 / xhigh | Planejamento entre setores ou complexidade ≥20 |
| Luna 6 / max | Triagem/planejamento com complexidade ≥35 |
| Sol 6.1 / medium | Revisão/diagnóstico com duas estratégias rejeitadas ou complexidade ≥35 |
| Sol 6.1 / high | Diagnóstico após três estratégias rejeitadas |

Complexidade = 2×min(campanhas,10) + 3×min(nichos distintos,5) + 8×avaliações rejeitadas + 3×avaliações parciais, considerando até cinco estratégias anteriores. Isso é uma pontuação operacional, não uma probabilidade de sucesso nem uma estimativa de custo. Falhas técnicas não entram nessa pontuação. A escolha manual de uma combinação permitida prevalece; nenhuma substituição silenciosa é admitida. Luna `ultra` não é oferecido: a instalação consultada anuncia até `max`.

Escolhas independentes na interface: **organização** (solo ou gestor+revisor), **tipo de chamada** (automático, triagem, planejamento, revisão, diagnóstico) e **modelo/esforço** (automático ou uma das cinco combinações). O tipo automático escolhe diagnóstico com ≥2 rejeições, planejamento com ≥3 nichos, triagem nos demais casos. Cada chamada registra versão do padrão, fatores, pontuação, motivo, combinação pedida/relatada e uso quando exposto. Solicitar um esforço superior não prova que ele melhora a decisão.

## Contratos constantes

- Janela de início: 15h00–15h09, Brasília UTC−3. Uma rodada estratégica por dia; até duas invocações de modelo, incluindo tentativas falhas. Sem recuperação tardia nem repetição automática. Uma chamada já iniciada pode terminar após a janela. Backend aberto é necessário.
- Solo usa uma chamada; dupla usa gestor e depois revisor em sessão separada, com o mesmo resumo e acesso ao plano proposto. O revisor tem contexto próprio, mas as avaliações são correlacionadas; não é revisão humana independente.
- Sessão ChatGPT local via Codex CLI; sem API paga de fallback. Tokens monetários e quota da assinatura são métricas distintas. Contagem de invocações não equivale a teto financeiro nem garante o número de requisições internas do serviço.
- O runtime deve relatar exatamente o modelo/esforço solicitado. Relato ausente ou divergente bloqueia a aplicação. Isso é evidência do relato do CLI, não auditoria independente do modelo servido.
- Resumo para inferência: IDs de campanhas, oferta, nicho, saldo, quantidade/pontuação de oportunidades e resultados agregados. Telefones, nomes dos leads e credenciais não são enviados ao modelo pelo controlador.
- O modelo propõe somente uma lista de campanhas existentes, motivo, hipótese e eventual abstenção. JSON inválido, IDs desconhecidos/repetidos ou autoridade adicional são recusados. O controlador executa serialmente e revalida pausas/estado.
- Seleção, qualificação, preparação e agenda de retornos são funções locais com dependências. Não são seis agentes LLM simultâneos. Dupla é uma delegação real adicional quando executada, limitada a dois contextos de inferência.
- O aprendizado usa avaliação humana e resultados registrados no CRM para orientar a próxima análise. Não modifica código, permissões, tetos, remetentes, modelo permitido ou padrões de envio sozinho.

## Autonomia e aprovação

Autônomo dentro da configuração autorizada: consultar a base, ordenar campanhas, preparar textos, cancelar contatos inelegíveis, promover retornos vencidos, executar captura já autorizada e registrar resultados. Pausar a gestão interrompe delegações seguintes; uma etapa externa já iniciada não pode ser desfeita.

Humano indispensável: aprovar texto/canal/destinatário de cada mensagem, confirmar autorização de contato, provisionar canais, aumentar tetos ou ampliar permissões. Mudança do contato ou texto invalida aprovação. Resposta/fechamento/recusa interrompe a cadência quando o status for atualizado no CRM; não há webhook de resposta implementado nesta versão.

## Avaliação do SOL

Histórico registra solo/dupla, hash do resumo, plano, tentativas, duração/tokens disponíveis e aceite humano. Esse registro é descritivo. Para testar superioridade, é necessário preregistrar unidades comparáveis, condições de qualidade, custo e latência e critérios de interrupção antes do piloto. Não comparar dias ou tarefas diferentes como se fossem pares; não reutilizar o resultado implementado como amostra independente. Ausência de custos/tokens deve permanecer desconhecida.

Inspirações: [Paperclip — agentes e heartbeats](https://docs.paperclip.ing/guides/org/agents/) e [aprovações](https://github.com/paperclipai/paperclip/blob/master/docs/guides/board-operator/approvals.md). Implementação nativa no CRM; Paperclip não instalado. CLI e saída estruturada: [OpenAI — modo não interativo](https://learn.chatgpt.com/docs/non-interactive-mode). Modelos: [Luna 6](https://developers.openai.com/api/docs/models/gpt-6-luna), [Sol 6.1](https://developers.openai.com/api/docs/models/gpt-6.1-sol).
