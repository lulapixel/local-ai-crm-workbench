"""Testes unitários e de integração para o domínio de Landing Pages (PR 2)."""

import json
import pytest
import sqlite3
import app as app_module
import db
import lp
from lp.copywriter import extrair_fatos_deterministicos, gerar_spec_fallback
from lp.repository import (
    arquivar_landing_page,
    atualizar_landing_page,
    criar_landing_page,
    obter_por_place_id,
    obter_por_slug,
    salvar_historico_brief,
    slug_existe,
)
from lp.service import (
    formatar_resposta_lp,
    gerar_slug_unico,
    obter_landing_page_por_place_id,
    obter_landing_page_por_slug,
    obter_ou_criar_landing_page,
    regenerar_conteudo_lp,
)
from lp.template_catalog import TEMPLATES, selecionar_template
from lp.validators import (
    sanitizar_telefone_whatsapp,
    sanitizar_texto,
    validar_cor,
    validar_e_sanitizar_spec,
)
import processar


@pytest.fixture
def conexao_memoria(monkeypatch, tmp_path):
    """Cria um banco SQLite temporário em arquivo de testes e executa migrações."""
    caminho_db = tmp_path / "test_leads_lp.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_db)

    conn = db.conectar()
    processar.preparar_banco(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(conexao_memoria):
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def criar_lead_teste(conn, place_id="place_123", nome="Clínica Áurea Estética", cidade="Curitiba", telefone="41999998888", nota=4.9, num_avaliacoes=42):
    conn.execute(
        """
        INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes, telefone, cidade, nicho, status)
        VALUES (?, ?, 'Clínica de Estética', 'Rua das Flores, 100', ?, ?, ?, ?, 'estética', 'novo')
        """,
        (place_id, nome, nota, num_avaliacoes, telefone, cidade),
    )
    conn.commit()


def test_import_modulo_lp():
    """Garante que o módulo backend.lp pode ser importado sem erros."""
    assert hasattr(lp, "migrar_lp")
    assert hasattr(lp, "obter_ou_criar_landing_page")
    assert hasattr(lp, "bp")


def test_selecao_template():
    """Valida o mapeamento por nicho e o fallback de template."""
    lead_estetica = {"nicho": "clínica de estética", "categoria": "Beleza"}
    assert selecionar_template(lead_estetica) == "estetica-premium"

    lead_desconhecido = {"nicho": "marcenaria", "categoria": "Móveis"}
    assert selecionar_template(lead_desconhecido) == "geral-conversao"

    lead_barbearia = {"nicho": "barbearia", "categoria": "Barbearia"}
    assert selecionar_template(lead_barbearia) == "geral-conversao"


def test_fallback_de_template_inexistente_e_neutro():
    lead = {"nome": "Empresa Teste", "categoria": "Marcenaria"}

    spec_desconhecido = gerar_spec_fallback(lead, "template-inexistente", "empresa-teste")
    spec_estetica = gerar_spec_fallback(lead, "estetica-premium", "empresa-teste-estetica")
    conteudo_desconhecido = json.dumps(spec_desconhecido, ensure_ascii=False).lower()
    conteudo_estetica = json.dumps(spec_estetica, ensure_ascii=False).lower()

    assert spec_desconhecido["palette"] == TEMPLATES["geral-conversao"]["default_palette"]
    assert spec_desconhecido["palette"] != TEMPLATES["estetica-premium"]["default_palette"]
    conteudo_desconhecido = conteudo_desconhecido.replace("consultationlabel", "")
    assert all(termo not in conteudo_desconhecido for termo in ("tratamentos", "consulta", "procedimentos", "avaliação"))
    assert spec_desconhecido["trust"] == []
    assert spec_desconhecido["testimonials"] == []
    assert "4.9" not in conteudo_desconhecido
    assert spec_estetica["palette"] == TEMPLATES["estetica-premium"]["default_palette"]
    assert "tratamentos" in conteudo_estetica


def test_geracao_slug_unico(conexao_memoria):
    criar_lead_teste(conexao_memoria, place_id="place_1", nome="Áurea Estética", cidade="Curitiba")

    slug1 = gerar_slug_unico(conexao_memoria, "Áurea Estética", "Curitiba", "place_1")
    assert "aurea-estetica-curitiba" in slug1

    # Inserir no banco para simular colisão
    criar_landing_page(conexao_memoria, "place_1", slug1, "estetica-premium", "{}")

    # Próximo slug para mesmo nome deve ter sufixo incremental ou alternativo
    slug2 = gerar_slug_unico(conexao_memoria, "Áurea Estética", "Curitiba", "place_2")
    assert slug2 != slug1


def test_validacao_spec_landing_page():
    spec_invalido = {
        "slug": "SLUG INVÁLIDO!",
        "brand": {"name": "<script>alert('xss')</script>Clínica teste"},
        "contact": {"whatsappNumber": "+55 (41) 99999-8888"},
        "palette": {"background": "cor-invalida", "accent": "#E5B869"},
        "services": [
            {"title": "Serviço 1", "priceFrom": -150.0},
        ],
        "testimonials": [
            {"name": "Maria", "rating": 10.0},
        ],
    }

    spec_limpo, avisos = validar_e_sanitizar_spec(spec_invalido)

    assert spec_limpo["slug"] == "slug-invalido"
    assert "<script>" not in spec_limpo["brand"]["name"]
    assert spec_limpo["brand"]["name"] == "Clínica teste"
    assert spec_limpo["contact"]["whatsappNumber"] == "5541999998888"
    assert spec_limpo["palette"]["background"] == "#0F0C10"  # fallback
    assert spec_limpo["palette"]["accent"] == "#E5B869"
    assert spec_limpo["services"][0]["priceFrom"] == 0.0
    assert spec_limpo["testimonials"][0]["rating"] == 5.0


def test_idempotencia_criacao_lp(conexao_memoria):
    criar_lead_teste(conexao_memoria, place_id="place_idempotente", nome="Empresa X", cidade="São Paulo")

    # Primeira chamada: cria
    res1 = obter_ou_criar_landing_page(conexao_memoria, "place_idempotente")
    assert res1["place_id"] == "place_idempotente"
    assert res1["status"] == "draft"
    lp_id_1 = res1["id"]

    # Segunda chamada com force_regenerate=False: retorna a mesma
    res2 = obter_ou_criar_landing_page(conexao_memoria, "place_idempotente", force_regenerate=False)
    assert res2["id"] == lp_id_1

    # Terceira chamada com force_regenerate=True: atualiza e mantém o id
    res3 = obter_ou_criar_landing_page(conexao_memoria, "place_idempotente", force_regenerate=True)
    assert res3["id"] == lp_id_1


def test_lead_inexistente_retorna_erro(conexao_memoria):
    with pytest.raises(ValueError, match="não encontrado"):
        obter_ou_criar_landing_page(conexao_memoria, "place_fantasma")


def test_exclusao_em_cascata_lead(conexao_memoria):
    criar_lead_teste(conexao_memoria, place_id="place_cascade", nome="Lead Deletavel")
    lp_data = obter_ou_criar_landing_page(conexao_memoria, "place_cascade")
    lp_id = lp_data["id"]

    # Apaga o lead
    conexao_memoria.execute("DELETE FROM leads WHERE place_id = 'place_cascade'")
    conexao_memoria.commit()

    # LP associada deve ser apagada via CASCADE
    lp_no_banco = obter_por_place_id(conexao_memoria, "place_cascade")
    assert lp_no_banco is None


def test_endpoints_api_lp(client, conexao_memoria):
    criar_lead_teste(conexao_memoria, place_id="place_api", nome="Clínica Luxo", cidade="Rio de Janeiro")

    # 1. POST criar LP
    resp = client.post("/api/leads/place_api/landing-page", json={"force_regenerate": True})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["place_id"] == "place_api"
    assert "slug" in data
    slug = data["slug"]
    lp_id = data["id"]

    # 2. GET consultar LP por place_id
    resp_get = client.get("/api/leads/place_api/landing-page")
    assert resp_get.status_code == 200
    assert resp_get.get_json()["id"] == lp_id

    # 3. GET consultar LP por slug
    resp_slug = client.get(f"/api/landing-pages/by-slug/{slug}")
    assert resp_slug.status_code == 200
    assert resp_slug.get_json()["id"] == lp_id

    # 3.1 GET consultar LP por id
    resp_id = client.get(f"/api/landing-pages/{lp_id}")
    assert resp_id.status_code == 200
    assert resp_id.get_json()["id"] == lp_id


    # 4. PATCH atualizar spec/status
    novos_dados = {"status": "published"}
    resp_patch = client.patch(f"/api/landing-pages/{lp_id}", json=novos_dados)
    assert resp_patch.status_code == 200
    assert resp_patch.get_json()["status"] == "published"
    assert resp_patch.get_json()["public_url"] == f"/demos/{slug}"

    # 5. POST regenerar
    resp_regen = client.post(f"/api/landing-pages/{lp_id}/regenerate", json={"sections": ["hero"], "tone": "premium"})
    assert resp_regen.status_code == 200

    # 6. POST arquivar
    resp_arch = client.post(f"/api/landing-pages/{lp_id}/archive")
    assert resp_arch.status_code == 200
    assert resp_arch.get_json()["status"] == "archived"


def test_migracao_lp_briefs_idempotente(conexao_memoria):
    """Garante que a migração de lp_briefs é idempotente e pode rodar repetidas vezes."""
    from lp.schema import migrar_lp_briefs
    # Executa a migração novamente
    migrar_lp_briefs(conexao_memoria)
    migrar_lp_briefs(conexao_memoria)

    colunas = [
        row["name"] if isinstance(row, dict) or hasattr(row, "keys") else row[1]
        for row in conexao_memoria.execute("PRAGMA table_info(lp_briefs)").fetchall()
    ]
    assert "landing_page_id" in colunas
    assert "change_type" in colunas
    assert "sections_json" in colunas
    assert "restored_from_version" in colunas
    assert "description" in colunas


def test_migracao_clean_pro_para_geral_conversao_preserva_linha(conexao_memoria):
    """O legado é atualizado uma vez sem alterar timestamps nem outras colunas."""
    from lp.schema import migrar_template_clean_pro_para_geral_conversao

    criar_lead_teste(conexao_memoria, place_id="legacy_clean_pro", nome="Empresa Legada")
    criar_lead_teste(conexao_memoria, place_id="already_general", nome="Empresa Atual")
    conexao_memoria.execute(
        """
        INSERT INTO landing_pages (
            place_id, slug, template_key, current_spec_json, status,
            schema_version, created_at, updated_at, published_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy_clean_pro",
            "legacy-clean-pro",
            "clean_pro",
            '{"hero":{"title":"Preservar"}}',
            "draft",
            1,
            "2026-01-01T00:00:00Z",
            "2026-02-02T00:00:00Z",
            None,
        ),
    )
    conexao_memoria.execute(
        """
        INSERT INTO landing_pages (
            place_id, slug, template_key, current_spec_json, status,
            schema_version, created_at, updated_at, published_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "already_general",
            "already-general",
            "geral-conversao",
            "{}",
            "published",
            2,
            "2026-01-03T00:00:00Z",
            "2026-02-03T00:00:00Z",
            "2026-02-04T00:00:00Z",
        ),
    )
    conexao_memoria.commit()

    assert migrar_template_clean_pro_para_geral_conversao(conexao_memoria) == 1
    legacy = conexao_memoria.execute(
        "SELECT template_key, current_spec_json, status, schema_version, created_at, updated_at, published_at "
        "FROM landing_pages WHERE place_id = ?",
        ("legacy_clean_pro",),
    ).fetchone()
    general = conexao_memoria.execute(
        "SELECT template_key, updated_at FROM landing_pages WHERE place_id = ?",
        ("already_general",),
    ).fetchone()
    assert tuple(legacy) == (
        "geral-conversao",
        '{"hero":{"title":"Preservar"}}',
        "draft",
        1,
        "2026-01-01T00:00:00Z",
        "2026-02-02T00:00:00Z",
        None,
    )
    assert tuple(general) == ("geral-conversao", "2026-02-03T00:00:00Z")
    assert migrar_template_clean_pro_para_geral_conversao(conexao_memoria) == 0


def test_historico_edicao_manual_e_json_identico(client, conexao_memoria):
    """Valida que edições manuais criam versões no histórico, mas envios de JSON idêntico são ignorados."""
    criar_lead_teste(conexao_memoria, place_id="place_hist_manual", nome="Empresa Historico")
    lp = obter_ou_criar_landing_page(conexao_memoria, "place_hist_manual")
    lp_id = lp["id"]

    import copy
    spec_modificado = copy.deepcopy(lp["spec"])
    spec_modificado["hero"]["title"] = "Título Editado Manualmente 1"


    resp = client.patch(f"/api/landing-pages/{lp_id}", json={"spec": spec_modificado})
    assert resp.status_code == 200

    resp_hist = client.get(f"/api/landing-pages/{lp_id}/history")
    assert resp_hist.status_code == 200
    versions = resp_hist.get_json()["versions"]
    assert len(versions) == 2
    assert versions[0]["version"] == 2
    assert versions[0]["change_type"] == "manual_edit"

    # 2. Re-envio de JSON idêntico -> NÃO cria v3
    resp_identical = client.patch(f"/api/landing-pages/{lp_id}", json={"spec": spec_modificado})
    assert resp_identical.status_code == 200

    resp_hist_2 = client.get(f"/api/landing-pages/{lp_id}/history")
    versions_2 = resp_hist_2.get_json()["versions"]
    assert len(versions_2) == 2  # Continuou com 2 versões


def test_regeneracao_parcial_isolamento_secoes(client, conexao_memoria):
    """Garante que regenerar o Hero não altera os serviços, contato nem paleta."""
    criar_lead_teste(conexao_memoria, place_id="place_isolamento", nome="Empresa Isolada")
    lp = obter_ou_criar_landing_page(conexao_memoria, "place_isolamento")
    lp_id = lp["id"]
    spec_anterior = lp["spec"]

    # Executa regeneração parcial do Hero
    resp = client.post(
        f"/api/landing-pages/{lp_id}/regenerate",
        json={"sections": ["hero"], "tone": "commercial", "instruction": "Foco em resultados rápida"},
    )
    assert resp.status_code == 200
    novo_spec = resp.get_json()["spec"]

    # Verificações de isolamento estrito
    assert novo_spec["services"] == spec_anterior["services"]
    assert novo_spec["contact"] == spec_anterior["contact"]
    assert novo_spec["palette"] == spec_anterior["palette"]
    assert novo_spec["testimonials"] == spec_anterior["testimonials"]
    assert novo_spec["faqs"] == spec_anterior["faqs"]


def test_validacoes_regeneracao_parcial_status_400(client, conexao_memoria):
    """Garante que seções inválidas ou tom inválido retornam erro 400 sem corromper o banco."""
    criar_lead_teste(conexao_memoria, place_id="place_val_400", nome="Empresa Valida 400")
    lp = obter_ou_criar_landing_page(conexao_memoria, "place_val_400")
    lp_id = lp["id"]

    # Seção inexistente
    resp1 = client.post(
        f"/api/landing-pages/{lp_id}/regenerate",
        json={"sections": ["secao_invalida_fantasma"]},
    )
    assert resp1.status_code == 400
    assert "inválida" in resp1.get_json()["erro"]

    # Tom inexistente
    resp2 = client.post(
        f"/api/landing-pages/{lp_id}/regenerate",
        json={"sections": ["hero"], "tone": "tom_inexistente"},
    )
    assert resp2.status_code == 400
    assert "inválido" in resp2.get_json()["erro"]


def test_endpoints_historico_e_restauracao(client, conexao_memoria):
    """Testa consulta individual de versão, restauração de versão antiga e erro 404 para versão inexistente."""
    criar_lead_teste(conexao_memoria, place_id="place_restaurar", nome="Empresa Restauracao")
    lp = obter_ou_criar_landing_page(conexao_memoria, "place_restaurar")
    lp_id = lp["id"]
    spec_v1 = lp["spec"]

    import copy
    spec_v2 = copy.deepcopy(spec_v1)
    spec_v2["hero"]["title"] = "Título v2 Alterado"
    client.patch(f"/api/landing-pages/{lp_id}", json={"spec": spec_v2})


    # Consulta de versão 1
    resp_v1 = client.get(f"/api/landing-pages/{lp_id}/history/1")
    assert resp_v1.status_code == 200
    assert resp_v1.get_json()["version"] == 1
    assert resp_v1.get_json()["spec"]["hero"]["title"] == spec_v1["hero"]["title"]

    # Consulta de versão inexistente -> 404
    resp_v404 = client.get(f"/api/landing-pages/{lp_id}/history/999")
    assert resp_v404.status_code == 404

    # Restauração da v1 -> gera v3 com restored_from_version=1
    resp_restore = client.post(f"/api/landing-pages/{lp_id}/history/1/restore")
    assert resp_restore.status_code == 200
    lp_restaurada = resp_restore.get_json()
    assert lp_restaurada["spec"]["hero"]["title"] == spec_v1["hero"]["title"]

    # Checa a lista de versões
    resp_hist = client.get(f"/api/landing-pages/{lp_id}/history")
    versions = resp_hist.get_json()["versions"]
    assert len(versions) == 3
    assert versions[0]["version"] == 3
    assert versions[0]["change_type"] == "version_restore"
    assert versions[0]["restored_from_version"] == 1


def test_publicacao_e_despublicacao_endpoints(client, conexao_memoria):
    """Testa o fluxo completo de publicar, consultar estado público, republicar e despublicar."""
    criar_lead_teste(conexao_memoria, place_id="place_pub_1", nome="Empresa Publicavel")
    lp = obter_ou_criar_landing_page(conexao_memoria, "place_pub_1")
    lp_id = lp["id"]
    slug = lp["slug"]

    # Tentativa de carregar página pública antes de publicar -> 404
    resp_pub_antes = client.get(f"/api/public/landing-pages/{slug}")
    assert resp_pub_antes.status_code == 404

    # Publicar
    resp_pub = client.post(f"/api/landing-pages/{lp_id}/publish")
    assert resp_pub.status_code == 200
    data_pub = resp_pub.get_json()
    assert data_pub["status"] == "published"
    assert data_pub["public_url"] is not None
    assert data_pub["publication_revision"] == 1

    # Consultar página pública
    resp_pub_depois = client.get(f"/api/public/landing-pages/{slug}")
    assert resp_pub_depois.status_code == 200
    pub_json = resp_pub_depois.get_json()
    assert pub_json["slug"] == slug
    assert "spec" in pub_json
    # Verificar que score ou campos internos do lead não vazam no payload público
    assert "nota" not in pub_json
    assert "score" not in pub_json
    assert "place_id" not in pub_json

    # Consultar status de publicação
    resp_status = client.get(f"/api/landing-pages/{lp_id}/publication-status")
    assert resp_status.status_code == 200
    status_json = resp_status.get_json()
    assert status_json["published"] is True
    assert status_json["publication_revision"] == 1

    # Despublicar
    resp_unpub = client.post(f"/api/landing-pages/{lp_id}/unpublish")
    assert resp_unpub.status_code == 200
    data_unpub = resp_unpub.get_json()
    assert data_unpub["status"] == "draft"

    # Tentativa de carregar pública após despublicar -> 404
    resp_pub_apos_unpub = client.get(f"/api/public/landing-pages/{slug}")
    assert resp_pub_apos_unpub.status_code == 404


def test_publicacao_lp_arquivada_bloqueada(client, conexao_memoria):
    """Garante que Landing Page arquivada não possa ser publicada."""
    criar_lead_teste(conexao_memoria, place_id="place_arq_pub", nome="Empresa Arquivada")
    lp = obter_ou_criar_landing_page(conexao_memoria, "place_arq_pub")
    lp_id = lp["id"]

    # Arquivar
    client.post(f"/api/landing-pages/{lp_id}/archive")

    # Tentar publicar -> 400
    resp = client.post(f"/api/landing-pages/{lp_id}/publish")
    assert resp.status_code == 400
    assert "arquivada" in resp.get_json()["erro"]


def test_analytics_event_types_whitelist_e_registro(client, conexao_memoria):
    """Testa whitelist de eventos, rejeição de tipos arbitrários e cálculo de estatísticas."""
    criar_lead_teste(conexao_memoria, place_id="place_analytics_1", nome="Empresa Analytics")
    lp = obter_ou_criar_landing_page(conexao_memoria, "place_analytics_1")
    lp_id = lp["id"]
    slug = lp["slug"]

    # Tentativa de registrar evento antes de publicar -> erro
    resp_unpub = client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "page_view", "session_id": "sess_1"},
    )
    assert resp_unpub.status_code == 400

    # Publicar a Landing Page
    client.post(f"/api/landing-pages/{lp_id}/publish")

    # Envio de evento com tipo inválido -> 400
    resp_inv = client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "hack_attempt_type", "session_id": "sess_1"},
    )
    assert resp_inv.status_code == 400
    assert "inválido" in resp_inv.get_json()["erro"]

    # Registrar eventos válidos
    client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "page_view", "session_id": "sess_1", "metadata": {"source": "direct"}},
    )
    client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "page_view", "session_id": "sess_2", "metadata": {"source": "direct"}},
    )
    client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "whatsapp_click", "session_id": "sess_1", "metadata": {"source": "hero_btn"}},
    )
    client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "simulator_start", "session_id": "sess_2"},
    )
    client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "simulator_complete", "session_id": "sess_2"},
    )

    # Consultar métricas no endpoint interno de analytics
    resp_metrics = client.get(f"/api/landing-pages/{lp_id}/analytics")
    assert resp_metrics.status_code == 200
    m = resp_metrics.get_json()

    assert m["page_views"] == 2
    assert m["estimated_sessions"] == 2
    assert m["whatsapp_clicks"] == 1
    assert m["simulator_starts"] == 1
    assert m["simulator_completions"] == 1
    assert m["last_view_at"] is not None


def test_fluxo_e2e_completo_landing_pages(client, conexao_memoria):
    """Valida o fluxo E2E completo e sequencial exigido pelo PR 8:
    1. criar lead
    2. gerar LP
    3. editar
    4. salvar
    5. regenerar Hero
    6. visualizar histórico
    7. restaurar versão
    8. publicar
    9. abrir link público
    10. registrar visualização
    11. clicar no WhatsApp
    12. verificar analytics
    13. despublicar
    """
    # 1. criar lead
    place_id = "place_e2e_full"
    criar_lead_teste(conexao_memoria, place_id=place_id, nome="Studio E2E Beauty", cidade="Recife")

    # 2. gerar LP
    resp_gerar = client.post(f"/api/leads/{place_id}/landing-page")
    assert resp_gerar.status_code == 200
    lp_data = resp_gerar.get_json()
    lp_id = lp_data["id"]
    slug = lp_data["slug"]
    assert lp_data["status"] == "draft"

    # 3 & 4. editar e salvar
    import copy
    spec_mod = copy.deepcopy(lp_data["spec"])
    spec_mod["hero"]["title"] = "Título E2E Editado Manualmente"
    resp_save = client.patch(f"/api/landing-pages/{lp_id}", json={"spec": spec_mod})
    assert resp_save.status_code == 200
    assert resp_save.get_json()["spec"]["hero"]["title"] == "Título E2E Editado Manualmente"

    # 5. regenerar Hero
    resp_regen = client.post(
        f"/api/landing-pages/{lp_id}/regenerate",
        json={"sections": ["hero"], "tone": "commercial", "instruction": "Destaque descontos de inauguração"},
    )
    assert resp_regen.status_code == 200
    assert "hero" in resp_regen.get_json()["spec"]

    # 6. visualizar histórico
    resp_hist = client.get(f"/api/landing-pages/{lp_id}/history")
    assert resp_hist.status_code == 200
    versions = resp_hist.get_json()["versions"]
    assert len(versions) >= 3

    # 7. restaurar versão (versão 1)
    resp_restore = client.post(f"/api/landing-pages/{lp_id}/history/1/restore")
    assert resp_restore.status_code == 200
    assert resp_restore.get_json()["spec"]["hero"]["title"] == lp_data["spec"]["hero"]["title"]

    # 8. publicar
    resp_pub = client.post(f"/api/landing-pages/{lp_id}/publish")
    assert resp_pub.status_code == 200
    assert resp_pub.get_json()["status"] == "published"

    # 9. abrir link público
    resp_public_get = client.get(f"/api/public/landing-pages/{slug}")
    assert resp_public_get.status_code == 200
    assert resp_public_get.get_json()["slug"] == slug

    # 10. registrar visualização
    resp_pv = client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "page_view", "session_id": "sess_e2e_1"},
    )
    assert resp_pv.status_code == 200

    # 11. clicar no WhatsApp
    resp_wa = client.post(
        f"/api/public/landing-pages/{slug}/events",
        json={"event_type": "whatsapp_click", "session_id": "sess_e2e_1", "metadata": {"source": "hero"}},
    )
    assert resp_wa.status_code == 200

    # 12. verificar analytics
    resp_analytics = client.get(f"/api/landing-pages/{lp_id}/analytics")
    assert resp_analytics.status_code == 200
    metrics = resp_analytics.get_json()
    assert metrics["page_views"] == 1
    assert metrics["whatsapp_clicks"] == 1

    # 13. despublicar
    resp_unpub = client.post(f"/api/landing-pages/{lp_id}/unpublish")
    assert resp_unpub.status_code == 200
    assert resp_unpub.get_json()["status"] == "draft"


def test_exclusao_em_cascata_lead_remove_lp_e_eventos(client, conexao_memoria):
    """Garante que deletar o lead remove em cascata LP, briefs/histórico e eventos de analytics."""
    place_id = "place_del_cascade"
    criar_lead_teste(conexao_memoria, place_id=place_id, nome="Empresa Exclusao")
    lp = obter_ou_criar_landing_page(conexao_memoria, place_id)
    lp_id = lp["id"]
    slug = lp["slug"]

    client.post(f"/api/landing-pages/{lp_id}/publish")
    client.post(f"/api/public/landing-pages/{slug}/events", json={"event_type": "page_view", "session_id": "s1"})

    # Excluir lead do banco
    conexao_memoria.execute("DELETE FROM leads WHERE place_id = ?", (place_id,))
    conexao_memoria.commit()

    # Verificar exclusão em cascata
    row_lp = conexao_memoria.execute("SELECT 1 FROM landing_pages WHERE id = ?", (lp_id,)).fetchone()
    assert row_lp is None

    row_brief = conexao_memoria.execute("SELECT 1 FROM lp_briefs WHERE landing_page_id = ?", (lp_id,)).fetchone()
    assert row_brief is None

    row_event = conexao_memoria.execute("SELECT 1 FROM landing_page_events WHERE landing_page_id = ?", (lp_id,)).fetchone()
    assert row_event is None
