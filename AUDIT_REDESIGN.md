# Auditoria e evolução do workbench de captação

Base examinada: `lulapixel/local-ai-crm-workbench` em `96ce0f5967d9b29accb9037d2ddc1eaeaefaa7bd` (arquivo público fixado). O trabalho foi desenvolvido em uma cópia isolada dessa revisão. Nenhum lead privado, chave, sessão ou busca real foi usado.

## Achados e correções

| Prioridade | Evidência no código-base | Consequência | Estado |
| --- | --- | --- | --- |
| Alta | `backend/processar.py` verificava site e Instagram em paralelo para todas as candidatas; só depois fazia `SELECT` por `place_id` ao salvar. | Leads já conhecidos repetiam consultas de enriquecimento a cada busca. | Corrigido por opção `apenas_novos`, ativa por padrão na nova interface e desligada por padrão na API para preservar clientes antigos. O filtro consulta IDs em lotes antes da rede e ignora duplicatas da captura. |
| Média | `backend/rotas_leads.py` aceitava linhas de busca, nichos e áreas repetidos. | A mesma combinação podia ser capturada mais de uma vez. | Corrigido com consolidação estável, preservando a primeira ocorrência. A interface mostra quantas combinações planeja e quantas repetições remove. |
| Média | O painel inicial apresentava cartões e métricas sem expor a fila priorizada já disponível em `/api/tarefas-hoje`. | Era preciso navegar para descobrir os próximos contatos; fácil captar mais antes de trabalhar a base. | Novo painel com oportunidades reais, prioridades, estados vazios e caminho de ação; novo cabeçalho e símbolo vetorial. |
| Baixa | A marca e o verde predominante não davam uma identidade consistente entre painel e captação. | Hierarquia visual fraca e mistura de sinais de produto com cor de canal. | Direção azul mineral e turquesa aplicada ao painel, navegação, botões e banner do Maps; cor do Instagram permanece associada ao canal. |

## Limites do modo econômico

O modo econômico reduz verificações posteriores à captura do Maps. Ele **não** evita a consulta inicial ao scraper ou à Google Places API; portanto, o número de combinações mostrado antes da busca não é uma estimativa de requisições faturáveis nem de economia em reais. Quando o modo está ativo, registros já presentes no CRM não recebem atualização dos campos do Maps ou da análise de site. Para atualizar esses registros, desative a opção e faça uma busca completa.

As contagens de `evitados_conhecidos` e `evitados_duplicados` aparecem no resultado do job como chamadas de análise web evitadas. Elas não são uma medição de preço, latência ou conversão.

## Verificação

- Testes focados de backend: `173 passed` (`test_processar.py`, `test_app.py`, `test_jobs.py`) com dados temporários e rede simulada.
- Frontend: `npm run lint` e `npm run build` passaram.
- Interface inspecionada no navegador com API local e diretório temporário vazio: painel, estado vazio, navegação para leads e contagem de repetições no formulário. Nenhuma busca foi iniciada.
- Suíte completa de backend: `514 passed` com dados temporários e dependências Windows carregadas no caminho de teste.

## Próxima validação de produto

Em uma cópia de dados autorizada, comparar duas capturas equivalentes com e sem `apenas_novos`: total de candidatos, análises web efetivamente chamadas, novos leads, tempo e custo da fonte configurada. O código atual comprova o salto de verificações desnecessárias em teste isolado; ainda não comprova redução monetária real nem melhora de conversão.
