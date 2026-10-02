# Mesa do gestor — implementação e validação

A entrada do ProspectOS passa a reunir recomendação explicada, oferta verificável e recebimentos informados. O objetivo é reduzir a decisão repetitiva do operador e dar visibilidade ao que depende de validação humana. Mantidos React/Vite/Flask/SQLite, a paleta azul-petróleo/verde e o fluxo existente da pesquisa.

## Decisões da implementação

- Preferências operacionais em duas tabelas locais novas; valores pessoais não aparecem nos defaults versionados. Leitura não inicializa nem altera registros. Agenda, modelo, limites, canais e permissões do bot permanecem nos respectivos controles.
- Respostas e retornos mantêm precedência. Cidade preferida desempata ações equivalentes. Cada ação explica setor, decisão humana e critério. Checklist da oferta determina a recomendação inicial quando não há conversa urgente.
- Oferta reúne público, resultado, escopo, preço proposto, prazo e demonstração. Revisões são declaradas pelo operador. Mudanças na base de uma revisão a invalidam. Uma demonstração presente no projeto não é automaticamente adequada para venda.
- O contexto estratégico recebe somente frente, prontidão, estilo de decisão e flags que negam novas permissões. Não recebe meta financeira, histórico pessoal, texto da oferta ou recebimentos. Uso em uma chamada real não foi executado nesta validação.
- Recebimentos são eventos locais em centavos inteiros, com data não futura, identificação idempotente e anulação que preserva histórico. Negócio fechado no CRM não vira receita automaticamente. O resumo do mês soma todos os registros válidos mesmo quando só os últimos 30 aparecem.
- Formulários preservam rascunhos em refetch e troca de mês; versões impedem sobrescrita entre janelas. Respostas da API de gestão usam no-store e as mutações passam pela proteção CSRF existente.
- O aplicativo local passa a abrir a mesa do gestor; a fila operacional continua acessível pelo menu.

## Direção visual

Reutilização dos tokens existentes: fundo #f3f5f6, superfície #ffffff, texto #1d3444, acento #15716c, painel #142f3c, linha #dce5e8. Tipografia Geist variável já instalada; display com peso moderado e números tabulares. Assinatura funcional: um resumo de decisão à esquerda, mandato do operador à direita e uma sequência de evidências (preparação, execução, recebimento). A sequência representa etapas reais, sem pressupor conversão. A versão escura conserva os tokens do workspace.

## Limites

Contratos remotos compartilham a preparação da demonstração; este recurso não procura vagas, não cadastra candidaturas e não comprova viabilidade comercial. Planejamento local e clareza de gestão não demonstram aumento de receita. O perfil pessoal completo e os registros financeiros permanecem locais. A mesa não publica conteúdo, transmite mensagens ou chama modelos ao ser aberta. A implementação não adiciona dependências nem amplia a política de execução.

## Verificação

A regressão completa passou com 661 testes backend, nove testes frontend e sete testes do launcher. TypeScript, lint e build passaram na versão final. A interface foi conferida em desktop, tablet e celular, incluindo conflito entre janelas, preservação de rascunho na troca de mês, recebimento e anulação. Testes de interface usam uma base fictícia e bloqueiam captura, modelos e transmissões. A instalação pessoal recebe somente preferências declaradas, sem receitas nem revisões comerciais fabricadas. Escopo, comandos e limites em [MANAGEMENT-VALIDATION.md](MANAGEMENT-VALIDATION.md).

## Recuperação

As funcionalidades de pesquisa e bot usam suas tabelas existentes. Para reverter a interface, restaurar os arquivos alterados a partir do baseline da entrega e reconstruir o frontend; não apagar o banco pessoal. As tabelas management_settings e management_receipts podem permanecer sem consumidor, preservando o histórico. A aplicação local do perfil produziu backup antes da mudança e verificou o hash das demais tabelas. Não restaurar um banco inteiro sobre dados posteriores.
