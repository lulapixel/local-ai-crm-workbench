# Pesquisa complementar após o plano, antes do código

O plano foi ampliado em identidade, estados e falhas de integração. Decisões abaixo foram fixadas antes dos patches funcionais.

## Identidade e relacionamento

Telefone normalizado será barreira conservadora de contato, não chave para fundir empresas. Filiais e centrais podem compartilhar número: a fila evita uma segunda abordagem e o operador corrige dados se necessário. Na seleção, eliminar duplicatas da rodada e contatos já em bot/central ou com status fora de novo. Na liberação, revalidar contra outros IDs. Registros antigos duplicados podem exigir resolução manual, nunca merge destrutivo.

Rejeitar texto é diferente de destinatário pedir não contato. A primeira ação cancela somente a cadência daquele lead; a segunda grava supressão por telefone e cancela cadências de IDs que compartilham o contato. Não inferir recusa a partir de ausência de resposta. Registro manual de respondeu/fechou/recusou exige confirmação explícita, sem IA e sem inventar webhook. A supressão continua após troca de ID ou remoção do lead; não há desbloqueio automático.

## Persistência e efeitos

[SQLite — transações](https://sqlite.org/lang_transaction.html) permite adquirir escrita com BEGIN IMMEDIATE, sujeita a disputa por escritor. Reserva e nova checagem devem ocorrer juntas. [AWS — outbox](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html) explica a separação entre gravação confirmada e efeito externo, e a necessidade de deduplicar processamento. Adaptação: resposta/recusa bloqueia envios queued na mesma transação; sending pode já ter efeito externo, portanto não prometer cancelamento de requisição em andamento. Não introduzir AWS/SQS.

[Resend — verificação](https://resend.com/docs/webhooks/verify-webhooks-requests) exige corpo bruto e assinatura; parser JSON sozinho não autentica eventos. Webhook não será exposto nesta onda: faltam conta e HTTPS. Registro humano deixa a operação utilizável enquanto isso, com origem explicitamente manual.

## Trabalho útil e observabilidade

Campanha pronta para decisão exige não estar pausada, ter saldo e pelo menos uma oportunidade local, retorno vencido elegível ou captura autorizada ainda não tentada hoje. Não transmitir snapshot vazio só para produzir uma estratégia. Promoção de follow-up é trabalho local; inferência só decide prioridades entre campanhas com algo a executar.

Heartbeat será estado do processo real, atualizado no loop. Configuração habilitada é distinta de relógio executando. Sem tick, mostrar inicialização pendente; heartbeat antigo, mostrar atenção. Agregados contabilizam preparadas, envios registrados, respostas e fechamentos por lead, sem atribuir causalidade ou converter contagem em retorno financeiro. Custo permanece null.

## Interface

[W3C — foco não oculto](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html) orienta scroll-margin abaixo da navegação. Links por seção, contraste com tokens existentes, inputs rotulados, estados com role=status e botões de pelo menos 32px favorecem teclado/mobile. Fila poderá ser filtrada por nome, telefone e campanha; nenhum filtro altera autorização. Lista separada de contatos em acompanhamento permite registrar resultado após envio, quando a mensagem sai da fila de revisão.

Decisão: implementar a onda local do plano agora. Integrações maiores, scoring novo e disponibilidade contínua ficam condicionados a dados/infra reais. Não ampliar número/modelos de chamadas nem ativar serviços durante o desenvolvimento.
