# Sistema de Landing Pages — ProspectOS

Documentação completa da arquitetura, persistência, API, geração por IA, histórico de versões, publicação externa e analytics do módulo de Landing Pages do ProspectOS.

---

## 1. Arquitetura Geral

O módulo de Landing Pages segue uma arquitetura em camadas no backend (`backend/lp/`) e no frontend (`frontend/src/features/landing-pages/`).

```text
[ Lead no ProspectOS ]
        │
        ▼
[ Geração determinística + IA (copywriter.py) ]
        │
        ▼
[ Persistência SQLite (landing_pages / lp_briefs) ]
        │
        ├── Editor Visual & Real-time Preview (/landing-pages/:id/edit)
        ├── Histórico de Versões & Restauração (/history)
        ├── Publicação & Sanitização (backend/lp/publishing/)
        └── Analytics & Eventos (/api/public/landing-pages/:slug/events)
```

### Estrutura de Arquivos Backend (`backend/lp/`)

- `__init__.py`: Módulo principal e registro de rotas.
- `schema.py`: Migrações SQL idempotentes para `landing_pages`, `lp_briefs` e `landing_page_events`.
- `repository.py`: Consultas e inserções SQL isoladas e transacionais.
- `service.py`: Regras de negócio, geração/regeneração com IA, versionamento, publicação e analytics.
- `routes.py`: Endpoints REST Flask.
- `copywriter.py`: Prompts e chamadas para IA (Gemini/Groq/Nvidia) e fallbacks determinísticos.
- `validators.py`: Sanitização de dados, validação de cores HSL/HEX e URLs.
- `publishing/`: Abstração de provedores de publicação (`base.py`, `local.py`, `remote.py`).
- `rate_limiter.py`: Limite de requisições em memória por IP para rotas públicas.

---

## 2. Tabelas e Migrações (`schema.py`)

### Tabela `landing_pages`
Armazena a Landing Page ativa do lead.

```sql
CREATE TABLE IF NOT EXISTS landing_pages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL UNIQUE,
    slug TEXT NOT NULL UNIQUE,
    template_key TEXT NOT NULL,
    current_spec_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'draft',
    public_id TEXT,
    public_url TEXT,
    publish_provider TEXT,
    publication_revision INTEGER DEFAULT 0,
    last_published_at TEXT,
    unpublished_at TEXT,
    schema_version INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    published_at TEXT,
    FOREIGN KEY (place_id) REFERENCES leads(place_id) ON DELETE CASCADE
);
```

### Tabela `lp_briefs` (Histórico de Versões)
Guarda o histórico imutável de alterações (geração inicial, edição manual, regeneração parcial por IA, restauração de versão).

```sql
CREATE TABLE IF NOT EXISTS lp_briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    place_id TEXT NOT NULL,
    landing_page_id INTEGER,
    change_type TEXT DEFAULT 'initial_generation',
    sections_json TEXT,
    restored_from_version INTEGER,
    description TEXT,
    spec_json TEXT NOT NULL,
    provedor TEXT,
    versao INTEGER NOT NULL DEFAULT 1,
    gerado_em TEXT NOT NULL,
    FOREIGN KEY (place_id) REFERENCES leads(place_id) ON DELETE CASCADE,
    FOREIGN KEY (landing_page_id) REFERENCES landing_pages(id) ON DELETE CASCADE
);
```

### Tabela `landing_page_events` (Analytics)
Registra eventos de acesso e conversão anonimizados.

```sql
CREATE TABLE IF NOT EXISTS landing_page_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    landing_page_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    session_id TEXT,
    metadata_json TEXT,
    occurred_at TEXT NOT NULL,
    FOREIGN KEY (landing_page_id) REFERENCES landing_pages(id) ON DELETE CASCADE
);
```

### Migração legada de template

No boot, `processar.migrar_banco` chama as migrações de LP e outreach. Elas convertem `clean_pro` para `geral-conversao` no `landing_pages.template_key` e no protótipo atual do conversion pack sem criar registros, regenerar conteúdo ou alterar versões e timestamps existentes.

---

## 3. Endpoints da API REST

### Gestão Interna (Dashboard / CRM)

| Método | Endpoint | Descrição |
|---|---|---|
| `POST` | `/api/leads/:place_id/landing-page` | Gera ou obtém a LP do lead |
| `GET` | `/api/leads/:place_id/landing-page` | Consulta a LP do lead |
| `GET` | `/api/landing-pages/:id` | Consulta LP por ID |
| `PATCH` | `/api/landing-pages/:id` | Atualiza spec / rascunho manual |
| `POST` | `/api/landing-pages/:id/regenerate` | Regeneração parcial com IA |
| `GET` | `/api/landing-pages/:id/history` | Lista histórico de versões |
| `GET` | `/api/landing-pages/:id/history/:version` | Detalhes de uma versão específica |
| `POST` | `/api/landing-pages/:id/history/:version/restore` | Restaura uma versão antiga |
| `POST` | `/api/landing-pages/:id/publish` | Publica a Landing Page |
| `POST` | `/api/landing-pages/:id/unpublish` | Despublica a Landing Page |
| `POST` | `/api/landing-pages/:id/republish` | Republica a Landing Page |
| `GET` | `/api/landing-pages/:id/publication-status` | Status de publicação e provedor |
| `GET` | `/api/landing-pages/:id/analytics` | Métricas de visualização e conversão |
| `POST` | `/api/landing-pages/:id/archive` | Arquiva a Landing Page |

### Endpoints Públicos (Sem autenticação do CRM)

| Método | Endpoint | Descrição |
|---|---|---|
| `GET` | `/api/public/landing-pages/:slug` | Retorna o spec sanitizado da LP publicada |
| `POST` | `/api/public/landing-pages/:slug/events` | Rastreia visualizações e conversões |

---

## 4. Publicação Externa & Sanitização

O ProspectOS separa rigorosamente o **Preview Interno** (`/demos/:slug?preview=1`) da **Publicação Externa**.

### Provedores de Publicação (`backend/lp/publishing/`)
- `LocalPublisher`: Usado quando nenhuma URL externa está configurada. Retorna link de prévia interna `/demos/:slug`.
- `RemotePublisher`: scaffold reservado para uma integração futura. URLs/chaves configuradas não ativam publicação por si só: o adapter atual falha fechado e nunca marca uma LP como publicada sem chamada remota confirmada. O `LocalPublisher` permanece o padrão até existir contrato HTTP autenticado, verify/rollback e teste E2E.

### Sanitização de Payload Público
Ao publicar ou servido no endpoint `/api/public/landing-pages/:slug`, o backend sanitiza o objeto removendo **quaisquer dados sensíveis ou internos do CRM**:
- Sem score interno do lead
- Sem notas, observações ou diagnósticos internos
- Sem histórico de prospecção ou tags internas
- Sem chaves de API ou logs

---

## 5. Analytics & Privacidade

Eventos aceitos (whitelist estrita):
- `page_view`
- `service_open`
- `simulator_start`
- `simulator_complete`
- `whatsapp_click`
- `instagram_click`

### Princípios de Privacidade:
1. **Sem Rastreamento Invasivo**: Não utiliza cookies de terceiros nem fingerprint de dispositivo.
2. **Session ID Local**: Gerado aleatoriamente no navegador do visitante (`crypto.randomUUID()`).
3. **Erros Silenciosos**: Falhas de analytics no frontend nunca bloqueiam a navegação ou o clique no WhatsApp.

---

## 6. Como Ativar Publicação Remota em Produção

Para preparar uma futura integração com infraestrutura pública de Landing Pages (ex: Vercel, Netlify ou servidor próprio):

Configure as seguintes variáveis no arquivo `.env` ou em Configurações:

```env
LP_PUBLIC_BASE_URL=https://lp.suaempresa.com
LP_PUBLISH_API_URL=https://api.suaempresa.com/v1/publish
LP_PUBLISH_API_KEY=sua_chave_secreta
```

Essas variáveis são apenas configuração preparatória no estado atual. Não
considere a resposta `published` como deploy remoto até que um adapter real
seja implementado, validado e habilitado explicitamente.

---

## 7. Validação e Testes Executados

### Backend Pytest
```bash
cd backend
python -m pytest
# Resultado: 365 testes aprovados
```

### Frontend Lint & Build
```bash
cd frontend
npm run lint
npm run build
# Resultado: 0 erros, build gerado com sucesso
```
