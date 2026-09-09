"""Blueprint com as rotas REST do Pacote de Conversão.
"""

import logging
from flask import Blueprint, jsonify, request

from outreach.service import (
    aprovar_pacote_conversao,
    aprovar_pacotes_em_lote,
    arquivar_pacote_conversao,
    arquivar_pacotes_em_lote,
    atualizar_pacote_manualmente,
    gerar_pacotes_em_lote,
    obter_fila_abordagem,
    obter_ou_gerar_pacote,
    obter_pacote_por_place_id,
    regenerar_secoes_pacote,
)

logger = logging.getLogger(__name__)

bp = Blueprint("outreach", __name__)

STATUS_PERMITIDOS = {"not_generated", "draft", "approved", "archived", None, ""}
SORT_PERMITIDOS = {"score", "highest_score", "reviews", "most_reviews", "recent", "most_recent", "name", "nome", None, ""}


@bp.route("/api/outreach/review-queue", methods=["GET"])
def consultar_fila_abordagem():
    """Consulta paginada da Central de Abordagens."""
    try:
        status = request.args.get("status")
        if status not in STATUS_PERMITIDOS:
            return jsonify({"erro": f"Status '{status}' inválido para a fila de revisão."}), 400

        search = request.args.get("search")
        niche = request.args.get("niche")
        city = request.args.get("city")

        min_score_str = request.args.get("min_score")
        min_score = None
        if min_score_str:
            try:
                min_score = int(min_score_str)
            except ValueError:
                return jsonify({"erro": "O parâmetro 'min_score' deve ser um número inteiro."}), 400

        channel = request.args.get("channel")

        has_lp_str = request.args.get("has_landing_page")
        has_landing_page = None
        if has_lp_str is not None:
            has_landing_page = has_lp_str.lower() in ("true", "1")

        lp_pub_str = request.args.get("landing_page_published")
        landing_page_published = None
        if lp_pub_str is not None:
            landing_page_published = lp_pub_str.lower() in ("true", "1")

        confidence = request.args.get("confidence")

        page_str = request.args.get("page", "1")
        try:
            page = max(1, int(page_str))
        except ValueError:
            return jsonify({"erro": "O parâmetro 'page' deve ser um número inteiro."}), 400

        page_size_str = request.args.get("page_size", "20")
        try:
            page_size = min(max(1, int(page_size_str)), 100)
        except ValueError:
            return jsonify({"erro": "O parâmetro 'page_size' deve ser um número inteiro."}), 400

        sort = request.args.get("sort", "score")
        if sort not in SORT_PERMITIDOS:
            return jsonify({"erro": f"Ordenação '{sort}' inválida."}), 400

        resultado = obter_fila_abordagem(
            status=status,
            search=search,
            niche=niche,
            city=city,
            min_score=min_score,
            channel=channel,
            has_landing_page=has_landing_page,
            landing_page_published=landing_page_published,
            confidence=confidence,
            page=page,
            page_size=page_size,
            sort=sort
        )
        return jsonify(resultado), 200
    except Exception:
        logger.exception("Erro ao consultar fila de abordagens.")
        return jsonify({"erro": "Erro interno ao consultar fila de abordagens."}), 500


@bp.route("/api/outreach/conversion-packs/bulk-generate", methods=["POST"])
def gerar_pacotes_em_lote_route():
    """Gera pacotes em lote (máx 10)."""
    try:
        dados = request.get_json() or {}
        place_ids = dados.get("place_ids")
        if not place_ids or not isinstance(place_ids, list):
            return jsonify({"erro": "O campo 'place_ids' é obrigatório e deve ser uma lista."}), 400

        approach = str(dados.get("approach", "consultative"))
        force_regenerate = bool(dados.get("force_regenerate", False))

        resultado = gerar_pacotes_em_lote(
            place_ids=place_ids,
            approach=approach,
            force_regenerate=force_regenerate
        )
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao gerar pacotes em lote.")
        return jsonify({"erro": "Erro interno ao gerar pacotes em lote."}), 500


@bp.route("/api/outreach/conversion-packs/bulk-approve", methods=["POST"])
def aprovar_pacotes_em_lote_route():
    """Aprova pacotes de conversão em lote."""
    try:
        dados = request.get_json() or {}
        pack_ids = dados.get("conversion_pack_ids")
        if not pack_ids or not isinstance(pack_ids, list):
            return jsonify({"erro": "O campo 'conversion_pack_ids' é obrigatório e deve ser uma lista."}), 400

        resultado = aprovar_pacotes_em_lote(pack_ids)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao aprovar pacotes em lote.")
        return jsonify({"erro": "Erro interno ao aprovar pacotes em lote."}), 500


@bp.route("/api/outreach/conversion-packs/bulk-archive", methods=["POST"])
def arquivar_pacotes_em_lote_route():
    """Arquiva pacotes de conversão em lote."""
    try:
        dados = request.get_json() or {}
        pack_ids = dados.get("conversion_pack_ids")
        if not pack_ids or not isinstance(pack_ids, list):
            return jsonify({"erro": "O campo 'conversion_pack_ids' é obrigatório e deve ser uma lista."}), 400

        resultado = arquivar_pacotes_em_lote(pack_ids)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao arquivar pacotes em lote.")
        return jsonify({"erro": "Erro interno ao arquivar pacotes em lote."}), 500



@bp.route("/api/leads/<place_id>/conversion-pack", methods=["POST"])
def gerar_ou_obter_pacote_lead(place_id):
    """Gera ou obtém o Pacote de Conversão para um lead.

    Payload opcional:
    {
        "force_regenerate": false,
        "approach": "consultative",
        "instruction": "..."
    }
    """
    try:
        dados = request.get_json(silent=True) or {}
        force_regenerate = bool(dados.get("force_regenerate", False))
        approach = str(dados.get("approach", "consultative"))
        instrucao = dados.get("instruction")

        pacote = obter_ou_gerar_pacote(
            place_id=place_id,
            force_regenerate=force_regenerate,
            approach=approach,
            instrucao_adicional=instrucao,
        )
        return jsonify(pacote), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception:
        logger.exception("Erro ao gerar/obter pacote de conversão para o lead %s", place_id)
        return jsonify({"erro": "Erro interno ao processar pacote de conversão."}), 500


@bp.route("/api/leads/<place_id>/conversion-pack", methods=["GET"])
def consultar_pacote_lead(place_id):
    """Consulta o Pacote de Conversão existente de um lead."""
    try:
        pacote = obter_pacote_por_place_id(place_id)
        if not pacote:
            return jsonify({"erro": f"Nenhum pacote de conversão encontrado para o lead '{place_id}'."}), 404
        return jsonify(pacote), 200
    except Exception:
        logger.exception("Erro ao consultar pacote de conversão para o lead %s", place_id)
        return jsonify({"erro": "Erro interno ao consultar pacote de conversão."}), 500


@bp.route("/api/conversion-packs/<int:pack_id>", methods=["PATCH"])
def atualizar_pacote(pack_id):
    """Atualização manual de um Pacote de Conversão."""
    try:
        dados = request.get_json()
        if not dados:
            return jsonify({"erro": "Payload JSON obrigatório."}), 400

        pacote_atualizado = atualizar_pacote_manualmente(pack_id, dados)
        return jsonify(pacote_atualizado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception:
        logger.exception("Erro ao atualizar pacote de conversão %d", pack_id)
        return jsonify({"erro": "Erro interno ao atualizar pacote de conversão."}), 500


@bp.route("/api/conversion-packs/<int:pack_id>/regenerate", methods=["POST"])
def regenerar_pacote(pack_id):
    """Regenera partes do Pacote de Conversão via IA com instrução opcional.

    Payload:
    {
        "sections": ["messages.followups", "objections"],
        "instruction": "Use uma abordagem mais curta"
    }
    """
    try:
        dados = request.get_json() or {}
        secoes = dados.get("sections") or ["messages"]
        instrucao = dados.get("instruction")

        pacote_regenerado = regenerar_secoes_pacote(
            pack_id=pack_id,
            sections=secoes,
            instruction=instrucao
        )
        return jsonify(pacote_regenerado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception:
        logger.exception("Erro ao regenerar seções do pacote %d", pack_id)
        return jsonify({"erro": "Erro interno ao regenerar pacote de conversão."}), 500


@bp.route("/api/conversion-packs/<int:pack_id>/approve", methods=["POST"])
def aprovar_pacote(pack_id):
    """Marca o Pacote de Conversão como aprovado."""
    try:
        pacote_aprovado = aprovar_pacote_conversao(pack_id)
        return jsonify(pacote_aprovado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 404
    except Exception:
        logger.exception("Erro ao aprovar pacote de conversão %d", pack_id)
        return jsonify({"erro": "Erro interno ao aprovar pacote de conversão."}), 500


@bp.route("/api/conversion-packs/<int:pack_id>/sequence/start", methods=["POST"])
def iniciar_sequencia_pacote(pack_id):
    """Inicia uma régua de abordagem a partir de um pacote aprovado."""
    try:
        from outreach.sequences_service import SequenceConflictError, iniciar_sequencia
        dados = request.get_json(silent=True) or {}
        channel = str(dados.get("channel", "whatsapp"))

        resultado = iniciar_sequencia(pack_id=pack_id, channel=channel)
        return jsonify(resultado), 200
    except SequenceConflictError as e:
        return jsonify({"erro": str(e)}), 409
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao iniciar sequência para o pacote %d", pack_id)
        return jsonify({"erro": "Erro interno ao iniciar sequência de abordagem."}), 500


@bp.route("/api/conversion-packs/<int:pack_id>/sequence", methods=["GET"])
def consultar_sequencia_pacote(pack_id):
    """Obtém os detalhes da sequência ativa associada a um pacote."""
    try:
        from outreach.sequences_service import obter_sequencia_detalhes
        resultado = obter_sequencia_detalhes(pack_id=pack_id)
        if not resultado:
            return jsonify({"erro": f"Nenhuma sequência encontrada para o pacote #{pack_id}."}), 404
        return jsonify(resultado), 200
    except Exception:
        logger.exception("Erro ao consultar sequência do pacote %d", pack_id)
        return jsonify({"erro": "Erro interno ao consultar sequência."}), 500


@bp.route("/api/outreach/sequences/<int:sequence_id>", methods=["GET"])
def consultar_sequencia_por_id(sequence_id):
    """Obtém detalhes de uma sequência pelo seu ID."""
    try:
        from outreach.sequences_service import obter_sequencia_detalhes
        resultado = obter_sequencia_detalhes(sequence_id=sequence_id)
        if not resultado:
            return jsonify({"erro": f"Sequência #{sequence_id} não encontrada."}), 404
        return jsonify(resultado), 200
    except Exception:
        logger.exception("Erro ao consultar sequência %d", sequence_id)
        return jsonify({"erro": "Erro interno ao consultar sequência."}), 500


@bp.route("/api/outreach/sequence-steps/<int:step_id>/mark-sent", methods=["POST"])
def marcar_etapa_enviada_route(step_id):
    """Confirma o envio de uma etapa pelo usuário."""
    try:
        from outreach.sequences_service import marcar_etapa_enviada
        dados = request.get_json(silent=True) or {}
        sent_at = dados.get("sent_at")
        channel = str(dados.get("channel", "whatsapp"))

        resultado = marcar_etapa_enviada(step_id=step_id, sent_at=sent_at, channel=channel)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao marcar etapa %d como enviada", step_id)
        return jsonify({"erro": "Erro interno ao confirmar envio da etapa."}), 500


@bp.route("/api/outreach/sequence-steps/<int:step_id>/skip", methods=["POST"])
def pular_etapa_route(step_id):
    """Pula uma etapa da cadência."""
    try:
        from outreach.sequences_service import pular_etapa
        dados = request.get_json(silent=True) or {}
        reason = dados.get("reason")

        resultado = pular_etapa(step_id=step_id, reason=reason)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao pular etapa %d", step_id)
        return jsonify({"erro": "Erro interno ao pular etapa."}), 500


@bp.route("/api/outreach/sequence-steps/<int:step_id>/reschedule", methods=["POST"])
def reagendar_etapa_route(step_id):
    """Reagenda a data prevista de disparo de uma etapa."""
    try:
        from outreach.sequences_service import reagendar_etapa
        dados = request.get_json() or {}
        scheduled_for = dados.get("scheduled_for")
        if not scheduled_for:
            return jsonify({"erro": "O campo 'scheduled_for' é obrigatório."}), 400

        resultado = reagendar_etapa(step_id=step_id, scheduled_for_iso=scheduled_for)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao reagendar etapa %d", step_id)
        return jsonify({"erro": "Erro interno ao reagendar etapa."}), 500


@bp.route("/api/outreach/sequences/<int:sequence_id>/pause", methods=["POST"])
def pausar_sequencia_route(sequence_id):
    """Pausa uma sequência de abordagem."""
    try:
        from outreach.sequences_service import pausar_sequencia
        resultado = pausar_sequencia(sequence_id=sequence_id)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao pausar sequência %d", sequence_id)
        return jsonify({"erro": "Erro interno ao pausar sequência."}), 500


@bp.route("/api/outreach/sequences/<int:sequence_id>/resume", methods=["POST"])
def retomar_sequencia_route(sequence_id):
    """Retoma uma sequência pausada deslocando as datas das etapas futuras."""
    try:
        from outreach.sequences_service import retomar_sequencia
        resultado = retomar_sequencia(sequence_id=sequence_id)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao retomar sequência %d", sequence_id)
        return jsonify({"erro": "Erro interno ao retomar sequência."}), 500


@bp.route("/api/outreach/sequences/<int:sequence_id>/stop", methods=["POST"])
def interromper_sequencia_route(sequence_id):
    """Interrompe ou cancela uma sequência (ex: após resposta)."""
    try:
        from outreach.sequences_service import interromper_sequencia
        dados = request.get_json(silent=True) or {}
        reason = str(dados.get("reason", "replied"))

        resultado = interromper_sequencia(sequence_id=sequence_id, reason=reason)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao interromper sequência %d", sequence_id)
        return jsonify({"erro": "Erro interno ao interromper sequência."}), 500


@bp.route("/api/outreach/daily-cockpit", methods=["GET"])
def consultar_cockpit_diario():
    """Consulta o Cockpit Diário de Prospecção com contadores e ações priorizadas.

    Query Params:
    - date: YYYY-MM-DD
    - timezone: Ex 'America/Recife'
    - category: 'all' | 'overdue' | 'today' | 'new' | 'paused' | 'upcoming' | 'replied'
    - search: string busca
    - channel: string canal
    - min_score: float
    - page: int (padrão 1)
    - page_size: int (padrão 20, max 100)
    """
    try:
        from outreach.daily_service import obter_cockpit_diario
        date_param = request.args.get("date")
        tz_param = request.args.get("timezone", "America/Recife")
        category_param = request.args.get("category", "all")
        search_param = request.args.get("search", "").strip()
        channel_param = request.args.get("channel", "all")

        min_score_raw = request.args.get("min_score")
        min_score = None
        if min_score_raw is not None and min_score_raw != "":
            try:
                min_score = float(min_score_raw)
            except ValueError:
                return jsonify({"erro": "O parâmetro 'min_score' deve ser um número válido."}), 400

        try:
            page = max(1, int(request.args.get("page", 1)))
        except ValueError:
            page = 1

        try:
            page_size = min(100, max(1, int(request.args.get("page_size", 20))))
        except ValueError:
            page_size = 20

        resultado = obter_cockpit_diario(
            date_str=date_param,
            tz_str=tz_param,
            category=category_param,
            search=search_param,
            channel=channel_param,
            min_score=min_score,
            page=page,
            page_size=page_size,
        )
        return jsonify(resultado), 200
    except Exception:
        logger.exception("Erro ao consultar cockpit diário de prospecção")
        return jsonify({"erro": "Erro interno ao consultar cockpit diário."}), 500


@bp.route("/api/leads/<place_id>/outreach/conversation", methods=["GET"])
def consultar_conversa_lead_route(place_id):
    """Retorna o histórico completo da conversa e timeline de interações do lead."""
    try:
        from outreach.conversations_service import obter_conversa_completa
        resultado = obter_conversa_completa(place_id)
        return jsonify(resultado), 200
    except Exception:
        logger.exception("Erro ao consultar conversa do lead %s", place_id)
        return jsonify({"erro": "Erro interno ao consultar conversa do lead."}), 500


@bp.route("/api/leads/<place_id>/outreach/responses", methods=["POST"])
def registrar_resposta_lead_route(place_id):
    """Registra uma resposta inbound recebida do prospect."""
    try:
        from outreach.conversations_service import registrar_resposta_lead
        dados = request.get_json() or {}
        classification = dados.get("classification")
        if not classification:
            return jsonify({"erro": "O campo 'classification' é obrigatório."}), 400

        content = dados.get("content", "")
        channel = str(dados.get("channel", "whatsapp"))
        occurred_at = dados.get("occurred_at")
        note = dados.get("note")

        resultado = registrar_resposta_lead(
            place_id=place_id,
            classification=classification,
            content=content,
            channel=channel,
            occurred_at=occurred_at,
            note=note,
        )
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao registrar resposta para o lead %s", place_id)
        return jsonify({"erro": "Erro interno ao registrar resposta do lead."}), 500


@bp.route("/api/leads/<place_id>/outreach/notes", methods=["POST"])
def registrar_nota_lead_route(place_id):
    """Registra uma observação interna do usuário na conversa."""
    try:
        from outreach.conversations_service import registrar_nota_interna
        dados = request.get_json() or {}
        content = dados.get("content")
        if not content or not content.strip():
            return jsonify({"erro": "O campo 'content' é obrigatório."}), 400

        channel = str(dados.get("channel", "whatsapp"))

        resultado = registrar_nota_interna(place_id=place_id, content=content, channel=channel)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao registrar nota interna para o lead %s", place_id)
        return jsonify({"erro": "Erro interno ao registrar nota interna."}), 500


@bp.route("/api/leads/<place_id>/outreach/calls", methods=["POST"])
def registrar_ligacao_lead_route(place_id):
    """Registra um contato via ligação telefônica."""
    try:
        from outreach.conversations_service import registrar_ligacao
        dados = request.get_json(silent=True) or {}
        content = dados.get("content")
        classification = dados.get("classification")
        objection_type = dados.get("objection_type")
        channel = str(dados.get("channel", "phone"))

        resultado = registrar_ligacao(
            place_id=place_id,
            content=content,
            classification=classification,
            objection_type=objection_type,
            channel=channel,
        )
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao registrar ligação para o lead %s", place_id)
        return jsonify({"erro": "Erro interno ao registrar ligação."}), 500


@bp.route("/api/outreach/interactions/<int:interaction_id>", methods=["PATCH"])
def atualizar_interacao_route(interaction_id):
    """Edita a classificação ou conteúdo de uma interação manual."""
    try:
        from outreach.conversations_service import atualizar_interacao_existente
        dados = request.get_json() or {}
        classification = dados.get("classification")
        content = dados.get("content")
        objection_type = dados.get("objection_type")

        resultado = atualizar_interacao_existente(
            interaction_id=interaction_id,
            classification=classification,
            content=content,
            objection_type=objection_type,
        )
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao atualizar interação %d", interaction_id)
        return jsonify({"erro": "Erro interno ao atualizar interação."}), 500


@bp.route("/api/outreach/interactions/<int:interaction_id>", methods=["DELETE"])
def excluir_interacao_route(interaction_id):
    """Exclui um registro de interação manual (não permitido para mensagens enviadas)."""
    try:
        from outreach.conversations_service import excluir_interacao_existente
        resultado = excluir_interacao_existente(interaction_id=interaction_id)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao excluir interação %d", interaction_id)
        return jsonify({"erro": "Erro interno ao excluir interação."}), 500


@bp.route("/api/outreach/interactions/<int:interaction_id>/suggest-reply", methods=["POST"])
def sugerir_resposta_route(interaction_id):
    """Gera uma sugestão de resposta curta assistida por IA."""
    try:
        from outreach.conversations_service import sugerir_resposta_assistida
        resultado = sugerir_resposta_assistida(interaction_id=interaction_id)
        return jsonify(resultado), 200
    except ValueError as e:
        return jsonify({"erro": str(e)}), 400
    except Exception:
        logger.exception("Erro ao sugerir resposta para a interação %d", interaction_id)
        return jsonify({"erro": "Erro interno ao gerar sugestão de resposta por IA."}), 500
