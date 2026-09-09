"""Serviço orquestrador do domínio de Outreach (Pacote de Conversão).

Integra diagnóstico determinístico, gerador de copy por IA/fallback, transações
com o domínio de Landing Pages e gerenciamento de versões.
"""

import json
import logging
from typing import Any, Dict, List, Optional

import db
from lp.service import obter_ou_criar_landing_page
from lp.template_catalog import normalizar_template_key
from outreach.copywriter import (
    gerar_pacote_com_ia,
    gerar_pacote_fallback,
    validar_e_sanitizar_pacote_copy,
)
from outreach.repository import (
    alterar_status_pacote,
    atualizar_pacote,
    obter_por_id,
    obter_por_place_id,
    salvar_novo_pacote,
)
from outreach.strategy import extrair_evidencias_e_estrategia

logger = logging.getLogger(__name__)


def _sincronizar_lp_com_prototipo(
    conexao, place_id: str, prototype_directives: Dict[str, Any]
) -> Optional[int]:
    """Assegura existência de uma LP para o lead e sincroniza apenas os campos
    comerciais autorizados no spec da LP de forma transacional.
    """
    try:
        template_key = normalizar_template_key(prototype_directives.get("templateKey"))
        lp_dict = obter_ou_criar_landing_page(conexao, place_id, template_key=template_key)
        if not lp_dict:
            return None

        lp_id = lp_dict["id"]
        current_spec = lp_dict.get("spec") or lp_dict.get("currentSpec") or {}

        # Atualiza apenas campos de orientação comercial no spec (hero, cta, focus)
        # sem destruir dados factual reais (reviews, telefone, endereço)
        hero = current_spec.get("hero")
        if not isinstance(hero, dict):
            hero = {}

        hero_angle = prototype_directives.get("heroAngle")
        primary_cta = prototype_directives.get("primaryCta")

        if hero_angle:
            hero["title"] = hero_angle
        if primary_cta:
            hero["primaryCta"] = primary_cta

        current_spec["hero"] = hero

        # Atualiza a LP no banco
        from datetime import datetime
        agora = datetime.now().isoformat(timespec="seconds")
        conexao.execute(
            """
            UPDATE landing_pages
            SET current_spec_json = ?, template_key = ?, updated_at = ?
            WHERE id = ?
            """,
            (json.dumps(current_spec, ensure_ascii=False), template_key, agora, lp_id),
        )
        return lp_id

    except Exception:
        logger.exception("Erro ao sincronizar diretrizes comerciais com a Landing Page.")
        return None


def obter_ou_gerar_pacote(
    place_id: str,
    force_regenerate: bool = False,
    approach: str = "consultative",
    instrucao_adicional: Optional[str] = None
) -> Dict[str, Any]:
    """Obtém o pacote existente ou gera um novo de forma transacional."""
    conexao = db.conectar()
    try:
        # 1. Verifica se lead existe
        lead = conexao.execute(
            "SELECT * FROM leads WHERE place_id = ?", (place_id,)
        ).fetchone()
        if not lead:
            raise ValueError(f"Lead com place_id '{place_id}' não encontrado.")

        lead_dict = dict(lead)

        # 2. Se já existe e não é força bruta, devolve o existente
        if not force_regenerate:
            pacote_existente = obter_por_place_id(conexao, place_id)
            if pacote_existente:
                return pacote_existente

        # 3. Diagnóstico comercial determinístico
        estrategia = extrair_evidencias_e_estrategia(lead_dict)

        # 4. Geração de Copy (IA ou Fallback)
        pacote_gerado = gerar_pacote_com_ia(lead_dict, estrategia, modo=approach, instrucao_adicional=instrucao_adicional)

        # 5. Sincronização transacional com a LP
        lp_id = _sincronizar_lp_com_prototipo(
            conexao, place_id, pacote_gerado["prototype"]
        )

        # 6. Salva ou Atualiza o pacote no banco
        pacote_existente = obter_por_place_id(conexao, place_id)
        if pacote_existente:
            pacote_salvo = atualizar_pacote(
                conexao=conexao,
                pack_id=pacote_existente["id"],
                strategy=pacote_gerado["strategy"],
                messages=pacote_gerado["messages"],
                objections=pacote_gerado["objections"],
                prototype=pacote_gerado["prototype"],
                landing_page_id=lp_id,
                change_type="ai_regeneration",
                provider=pacote_gerado.get("provider", "ia")
            )
        else:
            pacote_salvo = salvar_novo_pacote(
                conexao=conexao,
                place_id=place_id,
                landing_page_id=lp_id,
                strategy=pacote_gerado["strategy"],
                messages=pacote_gerado["messages"],
                objections=pacote_gerado["objections"],
                prototype=pacote_gerado["prototype"],
                provider=pacote_gerado.get("provider", "ia"),
                status="draft"
            )

        return pacote_salvo

    finally:
        conexao.close()


def obter_pacote_por_place_id(place_id: str) -> Optional[Dict[str, Any]]:
    conexao = db.conectar()
    try:
        return obter_por_place_id(conexao, place_id)
    finally:
        conexao.close()


def atualizar_pacote_manualmente(
    pack_id: int,
    payload: Dict[str, Any]
) -> Dict[str, Any]:
    conexao = db.conectar()
    try:
        pacote = obter_por_id(conexao, pack_id)
        if not pacote:
            raise ValueError(f"Pacote de conversão #{pack_id} não encontrado.")

        strategy = payload.get("strategy")
        messages = payload.get("messages")
        objections = payload.get("objections")
        prototype = payload.get("prototype")

        # Se houver atualização no protótipo, re-sincroniza com a LP
        lp_id = pacote["landingPageId"]
        if prototype:
            lp_id = _sincronizar_lp_com_prototipo(conexao, pacote["placeId"], prototype)

        resultado = atualizar_pacote(
            conexao=conexao,
            pack_id=pack_id,
            strategy=strategy,
            messages=messages,
            objections=objections,
            prototype=prototype,
            landing_page_id=lp_id,
            change_type="manual_edit"
        )
        return resultado
    finally:
        conexao.close()


def regenerar_secoes_pacote(
    pack_id: int,
    sections: List[str],
    instruction: Optional[str] = None
) -> Dict[str, Any]:
    """Regenera apenas seções específicas (ex: 'messages.followups', 'objections')
    preservando as edições das demais seções.
    """
    conexao = db.conectar()
    try:
        pacote_atual = obter_por_id(conexao, pack_id)
        if not pacote_atual:
            raise ValueError(f"Pacote #{pack_id} não encontrado.")

        lead = conexao.execute(
            "SELECT * FROM leads WHERE place_id = ?", (pacote_atual["placeId"],)
        ).fetchone()
        if not lead:
            raise ValueError(f"Lead associado '{pacote_atual['placeId']}' não encontrado.")

        lead_dict = dict(lead)
        estrategia = extrair_evidencias_e_estrategia(lead_dict)

        # Gera novo pacote completo como fonte de substituição
        pacote_novo = gerar_pacote_com_ia(
            lead_dict, estrategia, modo="consultative", instrucao_adicional=instruction
        )

        novas_messages = dict(pacote_atual["messages"])
        novas_objections = list(pacote_atual["objections"])
        novo_prototype = dict(pacote_atual["prototype"])

        if "messages" in sections or "messages.all" in sections:
            novas_messages = pacote_novo["messages"]
        elif "messages.followups" in sections:
            novas_messages["followups"] = pacote_novo["messages"]["followups"]
        elif "messages.initial" in sections:
            novas_messages["initial"] = pacote_novo["messages"]["initial"]

        if "objections" in sections:
            novas_objections = pacote_novo["objections"]

        if "prototype" in sections:
            novo_prototype = pacote_novo["prototype"]

        # Re-sanitiza
        payload_parcial = {
            "strategy": pacote_atual["strategy"],
            "messages": novas_messages,
            "objections": novas_objections,
            "prototype": novo_prototype
        }
        sanitizado = validar_e_sanitizar_pacote_copy(payload_parcial, lead_dict)

        # Atualiza no banco
        lp_id = _sincronizar_lp_com_prototipo(conexao, pacote_atual["placeId"], sanitizado["prototype"])
        return atualizar_pacote(
            conexao=conexao,
            pack_id=pack_id,
            strategy=sanitizado["strategy"],
            messages=sanitizado["messages"],
            objections=sanitizado["objections"],
            prototype=sanitizado["prototype"],
            landing_page_id=lp_id,
            change_type="ai_regeneration",
            provider=pacote_novo.get("provider", "ia")
        )
    finally:
        conexao.close()


def aprovar_pacote_conversao(pack_id: int) -> Dict[str, Any]:
    conexao = db.conectar()
    try:
        return alterar_status_pacote(conexao, pack_id, "approved")
    finally:
        conexao.close()


def arquivar_pacote_conversao(pack_id: int) -> Dict[str, Any]:
    conexao = db.conectar()
    try:
        from outreach.sequences_service import interromper_sequencias_por_pacote_arquivado
        interromper_sequencias_por_pacote_arquivado(conexao, pack_id)
        return alterar_status_pacote(conexao, pack_id, "archived")
    finally:
        conexao.close()


def calcular_score_lead(nota: Optional[float], num_avaliacoes: Optional[int], site_status: Optional[str]) -> int:
    pontos_nota = max(0.0, min((nota or 0.0) - 4.0, 1.0)) * 40
    pontos_avaliacoes = min(num_avaliacoes or 0, 100) * 0.3
    pontos_site = {"site_ruim": 22, "site_ok": 10}.get(site_status or "", 30)
    return round(pontos_nota + pontos_avaliacoes + pontos_site)


def obter_fila_abordagem(
    status: Optional[str] = "draft",
    search: Optional[str] = None,
    niche: Optional[str] = None,
    city: Optional[str] = None,
    min_score: Optional[int] = None,
    channel: Optional[str] = None,
    has_landing_page: Optional[bool] = None,
    landing_page_published: Optional[bool] = None,
    confidence: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "score"
) -> Dict[str, Any]:
    """Consulta paginada da fila de revisão de abordagens agregando leads, conversion_packs e landing_pages."""
    conexao = db.conectar()
    try:
        page = max(1, page)
        page_size = min(max(1, page_size), 100)

        sql_score = (
            "(MIN(MAX(COALESCE(l.nota, 0) - 4.0, 0), 1.0) * 40"
            " + MIN(COALESCE(l.num_avaliacoes, 0), 100) * 0.3"
            " + CASE COALESCE(l.site_status, '') WHEN 'site_ruim' THEN 22 WHEN 'site_ok' THEN 10 ELSE 30 END)"
        )

        condicoes = ["COALESCE(l.status, '') NOT IN ('ignorado', 'excluido')"]
        params: List[Any] = []

        # Filtro de status da fila:
        # not_generated -> sem conversion_pack
        # draft, approved, archived -> status exato do conversion_pack
        if status == "not_generated":
            condicoes.append("cp.id IS NULL")
        elif status in ("draft", "approved", "archived"):
            condicoes.append("cp.status = ?")
            params.append(status)

        if search and search.strip():
            termo = f"%{search.strip()}%"
            condicoes.append("(l.nome LIKE ? OR COALESCE(l.categoria, '') LIKE ? OR COALESCE(l.cidade, '') LIKE ?)")
            params.extend([termo, termo, termo])

        if niche and niche.strip():
            termo_nicho = f"%{niche.strip()}%"
            condicoes.append("(COALESCE(l.nicho, '') LIKE ? OR COALESCE(l.categoria, '') LIKE ?)")
            params.extend([termo_nicho, termo_nicho])

        if city and city.strip():
            condicoes.append("COALESCE(l.cidade, '') LIKE ?")
            params.append(f"%{city.strip()}%")

        if min_score is not None:
            condicoes.append(f"{sql_score} >= ?")
            params.append(float(min_score))

        if channel == "whatsapp":
            condicoes.append("((l.whatsapp_link IS NOT NULL AND l.whatsapp_link != '') OR (l.telefone IS NOT NULL AND l.telefone != ''))")
        elif channel == "phone":
            condicoes.append("(l.telefone IS NOT NULL AND l.telefone != '')")
        elif channel == "email":
            # se a tabela leads não tiver coluna email, tratamos como 0 resultados
            colunas_leads = [c[1] for c in conexao.execute("PRAGMA table_info(leads)").fetchall()]
            if "email" in colunas_leads:
                condicoes.append("(l.email IS NOT NULL AND l.email != '')")
            else:
                condicoes.append("1 = 0")

        if has_landing_page is not None:
            if has_landing_page:
                condicoes.append("lp.id IS NOT NULL")
            else:
                condicoes.append("lp.id IS NULL")

        if landing_page_published is not None:
            if landing_page_published:
                condicoes.append("lp.status = 'published'")
            else:
                condicoes.append("(lp.status IS NULL OR lp.status != 'published')")

        if confidence in ("low", "medium", "high"):
            condicoes.append("json_extract(cp.strategy_json, '$.confidence') = ?")
            params.append(confidence)

        where_clause = " WHERE " + " AND ".join(condicoes)

        # Ordenação
        ordem_sql = f"{sql_score} DESC, l.rowid ASC"
        if sort in ("reviews", "most_reviews"):
            ordem_sql = "COALESCE(l.num_avaliacoes, 0) DESC, " + sql_score + " DESC"
        elif sort in ("recent", "most_recent"):
            ordem_sql = "COALESCE(cp.updated_at, l.atualizado_em, l.visto_em, '') DESC"
        elif sort in ("name", "nome"):
            ordem_sql = "l.nome ASC"

        # 1. Total da consulta atual
        sql_total = f"""
            SELECT COUNT(*)
            FROM leads l
            LEFT JOIN conversion_packs cp ON l.place_id = cp.place_id
            LEFT JOIN landing_pages lp ON l.place_id = lp.place_id
            {where_clause}
        """
        total = conexao.execute(sql_total, params).fetchone()[0]

        # 2. Contagens operacionais por status (respeitando filtros globais exceto o status)
        condicoes_base = [c for c in condicoes if not c.startswith("cp.id IS NULL") and not c.startswith("cp.status =")]
        where_base = " WHERE " + " AND ".join(condicoes_base) if condicoes_base else ""
        params_base = [p for i, p in enumerate(params) if not (status in ("draft", "approved", "archived") and i == 0)]
        # Para garantir params_base limpo de status:
        if status in ("draft", "approved", "archived") and params and params[0] == status:
            params_base = params[1:]

        sql_counts = f"""
            SELECT
                SUM(CASE WHEN cp.id IS NULL THEN 1 ELSE 0 END) as count_not_generated,
                SUM(CASE WHEN cp.status = 'draft' THEN 1 ELSE 0 END) as count_draft,
                SUM(CASE WHEN cp.status = 'approved' THEN 1 ELSE 0 END) as count_approved,
                SUM(CASE WHEN cp.status = 'archived' THEN 1 ELSE 0 END) as count_archived
            FROM leads l
            LEFT JOIN conversion_packs cp ON l.place_id = cp.place_id
            LEFT JOIN landing_pages lp ON l.place_id = lp.place_id
            {where_base}
        """
        row_counts = conexao.execute(sql_counts, params_base).fetchone()
        counts = {
            "not_generated": row_counts["count_not_generated"] or 0 if row_counts else 0,
            "draft": row_counts["count_draft"] or 0 if row_counts else 0,
            "approved": row_counts["count_approved"] or 0 if row_counts else 0,
            "archived": row_counts["count_archived"] or 0 if row_counts else 0,
        }

        # 3. Busca de itens paginados
        offset = (page - 1) * page_size
        sql_items = f"""
            SELECT
                l.place_id, l.nome, l.categoria, l.nicho, l.cidade, l.nota, l.num_avaliacoes,
                l.telefone, l.whatsapp_link, l.site_status,
                cp.id as pack_id, cp.status as pack_status, cp.version as pack_version, cp.strategy_json, cp.messages_json,
                cp.updated_at as pack_updated_at,
                lp.id as lp_id, lp.status as lp_status, lp.slug as lp_slug, lp.public_url as lp_public_url
            FROM leads l
            LEFT JOIN conversion_packs cp ON l.place_id = cp.place_id
            LEFT JOIN landing_pages lp ON l.place_id = lp.place_id
            {where_clause}
            ORDER BY {ordem_sql}
            LIMIT ? OFFSET ?
        """
        items_params = list(params) + [page_size, offset]
        rows = conexao.execute(sql_items, items_params).fetchall()

        items = []
        for r in rows:
            r_dict = dict(r)
            queue_status = "not_generated" if not r_dict["pack_id"] else r_dict["pack_status"]
            score = calcular_score_lead(r_dict["nota"], r_dict["num_avaliacoes"], r_dict["site_status"])

            lead_data = {
                "place_id": r_dict["place_id"],
                "name": r_dict["nome"] or "",
                "niche": r_dict["nicho"] or r_dict["categoria"] or "",
                "city": r_dict["cidade"] or "",
                "score": score,
                "phone": r_dict["telefone"] or "",
                "whatsapp_link": r_dict["whatsapp_link"] or "",
                "rating": r_dict["nota"] or 0.0,
                "review_count": r_dict["num_avaliacoes"] or 0,
            }

            pack_data = None
            if r_dict["pack_id"]:
                strat = json.loads(r_dict["strategy_json"]) if r_dict.get("strategy_json") else {}
                msgs = json.loads(r_dict["messages_json"]) if r_dict.get("messages_json") else {}
                pack_data = {
                    "id": r_dict["pack_id"],
                    "status": r_dict["pack_status"],
                    "strategy": {
                        "opportunity": strat.get("opportunity", ""),
                        "commercialAngle": strat.get("commercialAngle", ""),
                        "confidence": strat.get("confidence", "medium"),
                    },
                    "initial_message": msgs.get("initial", ""),
                    "updated_at": r_dict["pack_updated_at"] or "",
                }

            lp_data = None
            if r_dict["lp_id"]:
                lp_data = {
                    "id": r_dict["lp_id"],
                    "status": r_dict["lp_status"] or "draft",
                    "preview_url": f"/demos/{r_dict['lp_slug']}" if r_dict.get("lp_slug") else f"/landing-pages/{r_dict['lp_id']}/edit",
                    "public_url": r_dict.get("lp_public_url") or "",
                }

            has_wa = bool(r_dict.get("whatsapp_link") or r_dict.get("telefone"))
            has_phone = bool(r_dict.get("telefone"))
            has_email = False

            channels = {
                "whatsapp": has_wa,
                "phone": has_phone,
                "email": has_email,
            }

            # Cálculo determinístico de alertas (warnings)
            warnings = []
            if not (has_wa or has_phone or has_email):
                warnings.append("missing_contact_channel")
            if not has_wa:
                warnings.append("missing_whatsapp")

            if not lp_data:
                warnings.append("missing_landing_page")
            elif lp_data["status"] != "published":
                warnings.append("landing_page_not_published")
            elif lp_data["status"] == "published" and not lp_data["public_url"]:
                warnings.append("prototype_without_public_url")

            if pack_data:
                if not (pack_data.get("initial_message") or "").strip():
                    warnings.append("empty_initial_message")
                if pack_data.get("strategy", {}).get("confidence") == "low":
                    warnings.append("low_confidence")
                if pack_data.get("status") == "archived":
                    warnings.append("pack_archived")

            sequence_data = None
            if r_dict["pack_id"]:
                from outreach.sequences_repository import obter_sequencia_por_pack_id, obter_etapas_sequencia
                seq = obter_sequencia_por_pack_id(conexao, r_dict["pack_id"])
                if seq:
                    # Encontra próxima etapa pronta ou pendente
                    etapas_seq = obter_etapas_sequencia(conexao, seq["id"])
                    proxima_etapa = None
                    if seq["status"] in ("active", "paused"):
                        for e in etapas_seq:
                            if e["status"] in ("ready", "pending"):
                                proxima_etapa = e
                                break

                    sequence_data = {
                        "id": seq["id"],
                        "status": seq["status"],
                        "conversion_pack_version": seq["conversion_pack_version"],
                        "version_outdated": (r_dict.get("pack_version", 1) > seq["conversion_pack_version"]),
                        "current_step_order": seq["current_step_order"],
                        "next_step": proxima_etapa,
                    }

            items.append({
                "queue_status": queue_status,
                "lead": lead_data,
                "conversion_pack": pack_data,
                "landing_page": lp_data,
                "sequence": sequence_data,
                "channels": channels,
                "warnings": warnings,
            })

        import math
        pages = math.ceil(total / page_size) if total > 0 else 1

        return {
            "items": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total": total,
                "pages": pages,
            },
            "counts": counts,
        }
    finally:
        conexao.close()


def gerar_pacotes_em_lote(
    place_ids: List[str],
    approach: str = "consultative",
    force_regenerate: bool = False
) -> Dict[str, Any]:
    """Gera pacotes de conversão em lote com limite e resultados individuais."""
    if not isinstance(place_ids, list):
        raise ValueError("O parâmetro 'place_ids' deve ser uma lista.")

    # Deduplicação mantendo ordem
    unique_ids = []
    seen = set()
    for pid in place_ids:
        if pid not in seen:
            seen.add(pid)
            unique_ids.append(pid)

    if len(unique_ids) > 10:
        raise ValueError("Máximo de 10 leads por lote.")

    results = []
    succeeded = 0
    failed = 0

    for pid in unique_ids:
        try:
            pacote = obter_ou_gerar_pacote(
                place_id=pid,
                force_regenerate=force_regenerate,
                approach=approach
            )
            results.append({
                "place_id": pid,
                "success": True,
                "conversion_pack_id": pacote["id"],
            })
            succeeded += 1
        except Exception as e:
            logger.warning("Falha ao gerar pacote em lote para o lead %s: %s", pid, e)
            results.append({
                "place_id": pid,
                "success": False,
                "error": str(e),
            })
            failed += 1

    return {
        "requested": len(unique_ids),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }


def aprovar_pacotes_em_lote(conversion_pack_ids: List[int]) -> Dict[str, Any]:
    """Aprova pacotes em lote validando estado draft e ausência de mensagens vazias."""
    if not isinstance(conversion_pack_ids, list):
        raise ValueError("O parâmetro 'conversion_pack_ids' deve ser uma lista.")

    results = []
    succeeded = 0
    failed = 0

    for pack_id in conversion_pack_ids:
        conexao = db.conectar()
        try:
            pacote = obter_por_id(conexao, pack_id)
            if not pacote:
                results.append({
                    "conversion_pack_id": pack_id,
                    "success": False,
                    "error": f"Pacote #{pack_id} não encontrado."
                })
                failed += 1
                continue

            if pacote["status"] != "draft":
                results.append({
                    "conversion_pack_id": pack_id,
                    "success": False,
                    "error": f"Pacote #{pack_id} está em status '{pacote['status']}' e não pode ser aprovado."
                })
                failed += 1
                continue

            # Validação crítica: mensagem inicial não pode ser vazia
            initial_msg = (pacote.get("messages") or {}).get("initial", "")
            if not (initial_msg or "").strip():
                results.append({
                    "conversion_pack_id": pack_id,
                    "success": False,
                    "error": f"Pacote #{pack_id} possui mensagem inicial vazia."
                })
                failed += 1
                continue

            alterar_status_pacote(conexao, pack_id, "approved")
            results.append({
                "conversion_pack_id": pack_id,
                "success": True
            })
            succeeded += 1
        except Exception as e:
            results.append({
                "conversion_pack_id": pack_id,
                "success": False,
                "error": str(e)
            })
            failed += 1
        finally:
            conexao.close()

    return {
        "requested": len(conversion_pack_ids),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }


def arquivar_pacotes_em_lote(conversion_pack_ids: List[int]) -> Dict[str, Any]:
    """Arquiva pacotes de conversão em lote."""
    if not isinstance(conversion_pack_ids, list):
        raise ValueError("O parâmetro 'conversion_pack_ids' deve ser uma lista.")

    results = []
    succeeded = 0
    failed = 0

    for pack_id in conversion_pack_ids:
        conexao = db.conectar()
        try:
            pacote = obter_por_id(conexao, pack_id)
            if not pacote:
                results.append({
                    "conversion_pack_id": pack_id,
                    "success": False,
                    "error": f"Pacote #{pack_id} não encontrado."
                })
                failed += 1
                continue

            from outreach.sequences_service import interromper_sequencias_por_pacote_arquivado
            interromper_sequencias_por_pacote_arquivado(conexao, pack_id)
            alterar_status_pacote(conexao, pack_id, "archived")
            results.append({
                "conversion_pack_id": pack_id,
                "success": True
            })
            succeeded += 1
        except Exception as e:
            results.append({
                "conversion_pack_id": pack_id,
                "success": False,
                "error": str(e)
            })
            failed += 1
        finally:
            conexao.close()

    return {
        "requested": len(conversion_pack_ids),
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }
