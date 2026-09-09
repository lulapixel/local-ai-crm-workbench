# Servidor MCP (Model Context Protocol) do ProspectOS

O ProspectOS oferece um servidor MCP oficial local que permite que assistentes e agentes de IA (como Claude Desktop, Antigravity, Cursor, VSCode Copilot) consultem e operem o CRM com ferramentas seguras, documentadas e padronizadas.

---

## 1. Requisitos

1. **Python 3.10 ou superior** instalado no ambiente do backend.
2. Dependências do backend instaladas (`pip install -r requirements.txt`).
3. Aplicativo ProspectOS em execução (interface desktop ou backend Flask).

---

## 2. Inicialização do Servidor MCP

### Execução em Desenvolvimento (Código-fonte)

No diretório `backend`:

```powershell
cd backend
& "C:\Caminho\Para\python.exe" -m mcp_server
```

Use um interpretador absoluto que tenha as dependências `mcp`, Flask e `requests`; não dependa do launcher `py` estar disponível no PATH.

### Execução Empacotada (Instalação no Windows)

Caso o aplicativo tenha sido instalado via instalador executável:

```powershell
"C:\Program Files\ProspectOS\ProspectOS-MCP.exe"
```

---

## 3. Configuração nos Clientes MCP

### Exemplo de Configuração (`mcp-config.json`)

```json
{
  "mcpServers": {
    "prospectos": {
      "command": "C:\\Caminho\\Para\\python.exe",
      "args": [
        "-m",
        "mcp_server"
      ],
      "cwd": "C:\\Caminho\\Para\\ProspectOS\\backend"
    }
  }
}
```

Para a versão instalada no Windows:

```json
{
  "mcpServers": {
    "prospectos": {
      "command": "C:\\Program Files\\ProspectOS\\ProspectOS-MCP.exe"
    }
  }
}
```

---

## 4. Classificação de Risco e Ferramentas

### Nível 0 — Leitura
- `prospectos_status`: Verifica saúde do backend e se há jobs ativos.
- `listar_leads_maps`: Lista leads do Maps com filtros e pontuação (score).
- `obter_lead_maps`: Detalhes completos de um lead do Maps por `place_id`.
- `listar_nichos_maps`: Nichos cadastrados no CRM.
- `obter_historico_status_maps`: Histórico de trocas de status.
- `listar_followups_maps`: Follow-ups pendentes.
- `listar_posts_instagram`: Posts analisados.
- `listar_leads_instagram`: Leads capturados do Instagram por post.
- `obter_lead_instagram`: Detalhes de lead do Instagram por `lead_id`.
- `obter_historico_status_instagram`: Histórico do Instagram.
- `obter_metricas`: Métricas gerais de conversão e totais.
- `obter_funil`: Estágios e volume do funil de vendas.
- `obter_desempenho_por_nicho`: Análise comparativa por nicho.
- `obter_tarefas_hoje`: Tarefas prioritárias do dia.
- `consultar_status_busca_maps`: Progresso da busca no Maps.
- `listar_historico_buscas_maps`: Histórico de buscas efetuadas.
- `consultar_status_analise_instagram`: Progresso de análise do Instagram.
- `obter_contexto_producao_site`: Handoff somente-leitura de oportunidade para produção de site (`site-opportunity/v1`).

### Nível 1 — Mutação Reversível do CRM
- `atualizar_status_lead_maps` / `atualizar_status_lead_instagram`
- `atualizar_observacoes_maps` / `atualizar_observacoes_instagram`
- `definir_tags_maps` / `definir_tags_instagram`
- `agendar_followup_maps` / `agendar_followup_instagram`
- `marcar_followup_enviado_maps` / `marcar_followup_enviado_instagram`
- `registrar_resultado_site`: Registra o resultado de produção em um bloco idempotente de `lead.observacoes` (`site-result/v1`).
- `exportar_contexto_obsidian`: Exporta um contexto sanitizado para uma nota local do vault Obsidian; exige `confirmar=true` e `PROSPECTOS_OBSIDIAN_VAULT`.

### Nível 2 — Operações Sensíveis / Acesso Externo (Exigem `confirmar=true`)
- `iniciar_busca_maps`: Inicia novo scraping no Maps.
- `iniciar_analise_post_instagram`: Inicia análise de post no Instagram.
- `retomar_analise_instagram`: Retoma job pausado.
- `reanalisar_site_maps`: Recarrega e analisa site no PageSpeed.
- `gerar_mensagem_maps` (quando `forcar_nova=true`).

---

## 5. Política de Segurança

1. **Stdout Reservado**: O stdout é mantido exclusivamente para mensagens JSON-RPC do protocolo MCP.
2. **Sanitização de Dados**: Chaves de API (Gemini, Groq, NVIDIA), senhas do Instagram, proxies e tokens de sessão são filtrados via allowlists antes de retornar ao agente.
3. **Sem Exclusão Definitiva**: Operações de deleção no banco não são expostas no MCP.
4. **Local Host Only**: O servidor MCP se conecta unicamente à instância local (`127.0.0.1`).

---

## 5.1. Handoff ProspectOS → Sol Advisor (V1 congelado)

O ProspectOS mantém a propriedade do contexto comercial, CRM, conversion pack e demonstração de Landing Page. O Sol Advisor mantém planejamento, implementação, revisão, preview e deploy.

- `obter_contexto_producao_site(place_id, nivel)` retorna o contrato `site-opportunity/v1`. `nivel="demo"` permite avaliar a demonstração existente; `nivel="full"` só é elegível quando `conversion_pack.status == "approved"` **e** o CRM está em `respondeu` ou `fechou`.
- A produção completa requer esse sinal comercial humano; as ferramentas não criam leads, sites, filas, builds ou publicações automáticas.
- `registrar_resultado_site(...)` retorna/guarda `site-result/v1` no bloco marcado de observações sem apagar notas manuais. O registro não publica nem altera o funil comercial.
- `exportar_contexto_obsidian(...)` grava somente a nota gerenciada do lead no vault configurado; a operação não altera o CRM, não inicia sequência e preserva notas humanas não gerenciadas.

---

## 6. Solução de Problemas

- **Erro `BACKEND_OFFLINE`**: Certifique-se de que a aplicação desktop ProspectOS esteja aberta antes de invocar comandos do agente.
- **Porta Dinâmica**: O servidor descobre automaticamente a porta em uso lendo o arquivo `%APPDATA%\ProspectOS\porta.txt`.
- **Logs**: Consulte `%APPDATA%\ProspectOS\logs\mcp.log` para detalhes técnicos de execução.
