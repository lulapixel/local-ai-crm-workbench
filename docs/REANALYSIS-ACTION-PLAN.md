# Plano antes da implementação

Sequência exigida: reanálise → plano → pesquisa complementar das escolhas → implementação → validação. Base: `d03b4b3`. Escopo local; sem novas contas, publicação, gasto ou contato externo. Prioridade usa gravidade observada, benefício operacional e esforço relativo, não ROI inventado.

| Ordem | Mudança | Benefício | Complexidade relativa | Aceite |
|---|---|---|---|---|
| P0 | Deduplicar telefone normalizado na seleção e liberação | Evitar abordagem repetida entre IDs/campanhas | Média | IDs diferentes/formatos diferentes não criam dois primeiros contatos; conflito no envio é bloqueado |
| P0 | Supressão persistente e registro manual de resposta | Interromper cadência e respeitar pedido de não contato após recaptura | Média | Não-contato cancela fila e envio queued, revalida antes de rede; registro repetido não duplica evento |
| P1 | Snapshot só com trabalho útil | Poupar chamadas quando fila/limite já resolvem trabalho | Baixa | Sem saldo, oportunidades ou retorno vencido, nenhuma inferência é solicitada |
| P1 | Centro de operação, heartbeat e métricas honestas | Revelar relógio parado, pendências e próximo passo | Média | API de leitura sem credenciais; painel distingue ativo/inativo e inferência não medida |
| P1 | Fila pesquisável, navegação por seções e resultados na mesma página | Menos procura e alternância de telas | Média | Mobile sem overflow; teclado/foco e estados vazios úteis; aprovação continua individual |
| P1 | Testes de integração e relatório de evidência | Impedir regressões no fluxo e registrar limites | Média | Suite backend, build/lint e inspeção visual; nenhum provider/canal real nos testes |

Esta é a onda local escolhida para implementar após pesquisa complementar. Os itens abaixo têm dependências materiais; permanecerão como roadmap explícito, sem simular que foram ativados.

| Onda posterior | Dependência | Primeiro experimento e critério de avanço |
|---|---|---|
| Reconciliação de eventos Resend/Meta | Conta, segredo de assinatura, endpoint HTTPS e autorização | Evento autenticado, replay deduplicado, timeout e ordem invertida; nenhum envio adicional implícito |
| Custo de captação e fresh data | Fonte real/quotas autorizadas, dados representativos | Comparar máscara atual com IDs+detalhes; medir requisições/SKU, tempo e cobertura antes de escolher |
| Scoring fit/engagement e propostas | Respostas/propostas reais e critérios comerciais | Separar adequação de intenção; explicações por regra; preservar ausência de dados |
| Worker durável e disponibilidade | Necessidade de operar com notebook fechado, orçamento escolhido | Crash/restart e ownership do job; adotar serviço só se requisito justificar custo |
| CI e qualidade contínua | Runtime limpo reproduzível de Windows/Linux | Pipeline sem segredos, dependências travadas, teste de contratos; não chamar suite local de CI |
| Piloto SOL solo/dupla | Primeira inferência real confirmada, tarefas equivalentes e gate experimental | Preregistrar amostras, qualidade, recursos e latência; abstenção e falha contam separadamente |
| Produto/receita | Oferta, nicho e cliente voluntário | Demonstração com benefício verificável, sem prometer renda; medir tempo humano por oportunidade aceita |

## Design escolhido antes do patch

Assunto: estação pessoal de prospecção, operada por uma pessoa com orçamento baixo. Trabalho principal da página: localizar a próxima ação segura, não celebrar quantidade de agentes.

Paleta mantém azul mineral `#14344b`, turquesa `#25808a`, azul profundo `#0e2535`, destaque claro `#d8efeb`, atenção `#995d24` e superfícies por tokens do tema. Geist permanece corpo/display; números usam alinhamento tabular e fonte monoespaçada do sistema como utilidade. Sem download de fontes ou nova identidade comercial.

Layout escolhido: cabeçalho compacto → centro de operação com próximos passos → navegação por âncoras → fila e resultados → configuração/agenda existentes. Assinatura: trilho de decisões que liga estado observado à ação concreta. Comparado a hero/orbita decorativa, dá informação útil acima da dobra. Não usar abas com semântica falsa; links internos mantêm navegação nativa e acessível.

## Pesquisa complementar a concluir antes do código

Verificar semântica de supressão e identidade de contato; distinguir rejeição de texto de recusa do destinatário; definir o que conta como trabalho útil; conferir efeitos em outbox/pausa; consultar boas práticas de fila/resultado e foco/acessibilidade. Registrar decisões em `RESEARCH-EXPANSION.md` antes de aplicar patches funcionais.
