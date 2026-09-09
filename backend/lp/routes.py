"""Endpoints Flask do domínio de Landing Pages.

Fornece a API REST para criação, consulta, edição, regeneração e arquivamento de LPs.
"""

import logging
from flask import Blueprint, jsonify, request
import db
from .rate_limiter import rate_limit_publico
from .service import (
    arquivar_lp,
    atualizar_landing_page_spec,
    despublicar_landing_page,
    listar_historico_landing_page,
    obter_analytics_landing_page,
    obter_landing_page_por_id,
    obter_landing_page_por_place_id,
    obter_landing_page_por_slug,
    obter_landing_page_publica,
    obter_ou_criar_landing_page,
    obter_status_publicacao,
    obter_versao_historico_landing_page,
    publicar_landing_page,
    regenerar_conteudo_lp,
    registrar_evento_publico_lp,
    republicar_landing_page,
    restaurar_versao_landing_page,
)


logger = logging.getLogger(__name__)

bp = Blueprint("landing_pages", __name__)


@bp.route("/api/landing-pages/<int:lp_id>", methods=["GET"])
def consultar_lp_por_id(lp_id):
    """Consulta a Landing Page pelo seu ID numérico."""
    conexao = db.conectar()
    try:
        resultado = obter_landing_page_por_id(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao consultar Landing Page por id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao consultar a Landing Page."}), 500
    finally:
        conexao.close()



@bp.route("/api/leads/<place_id>/landing-page", methods=["POST"])
def criar_ou_obter_lp(place_id):
    """Cria uma Landing Page para o lead ou retorna a existente.

    Body (opcional):
    {
        "template_key": "estetica-premium",
        "force_regenerate": false
    }
    """
    dados = request.get_json(silent=True) or {}
    template_key = dados.get("template_key")
    force_regenerate = bool(dados.get("force_regenerate", False))

    conexao = db.conectar()
    try:
        resultado = obter_ou_criar_landing_page(
            conexao, place_id, template_key=template_key, force_regenerate=force_regenerate
        )
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception as exc:
        logger.exception("Erro ao gerar/obter Landing Page para place_id=%s", place_id)
        return jsonify({"erro": "Falha interna ao processar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/leads/<place_id>/landing-page", methods=["GET"])
def consultar_lp_do_lead(place_id):
    """Consulta a Landing Page ativa de um determinado lead."""
    conexao = db.conectar()
    try:
        resultado = obter_landing_page_por_place_id(conexao, place_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao consultar Landing Page para place_id=%s", place_id)
        return jsonify({"erro": "Falha interna ao consultar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/by-slug/<slug>", methods=["GET"])
def consultar_lp_por_slug(slug):
    """Endpoint público/preview para carregar a configuração da Landing Page pelo slug."""
    conexao = db.conectar()
    try:
        resultado = obter_landing_page_por_slug(conexao, slug)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao consultar Landing Page por slug=%s", slug)
        return jsonify({"erro": "Falha interna ao consultar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>", methods=["PATCH"])
def atualizar_lp(lp_id):
    """Atualiza o spec JSON ou status da Landing Page."""
    dados = request.get_json(silent=True) or {}
    spec_in = dados.get("spec") or dados
    novo_status = dados.get("status")

    if not isinstance(spec_in, dict):
        return jsonify({"erro": "Corpo da requisição deve conter um objeto 'spec' ou campos JSON."}), 400

    conexao = db.conectar()
    try:
        resultado = atualizar_landing_page_spec(conexao, lp_id, spec_in, novo_status=novo_status)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao atualizar Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao atualizar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/regenerate", methods=["POST"])
def regenerar_lp(lp_id):
    """Regenera parcial ou totalmente o conteúdo da Landing Page via IA.

    Body (opcional):
    {
        "sections": ["hero", "faqs"],
        "tone": "premium",
        "instruction": "Destaque atendimento personalizado"
    }
    """
    dados = request.get_json(silent=True) or {}
    secoes = dados.get("sections")
    tone = dados.get("tone", "premium")
    instruction = dados.get("instruction", "")

    conexao = db.conectar()
    try:
        resultado = regenerar_conteudo_lp(
            conexao, lp_id, secoes=secoes, tone=tone, instruction=instruction
        )
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 400
    except Exception:
        logger.exception("Erro ao regenerar Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao regenerar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/history", methods=["GET"])
def consultar_historico_lp(lp_id):
    """Retorna a lista resumida de versões do histórico de uma Landing Page."""
    conexao = db.conectar()
    try:
        resultado = listar_historico_landing_page(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao listar histórico para Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao listar histórico."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/history/<int:version>", methods=["GET"])
def consultar_versao_historico_lp(lp_id, version):
    """Retorna os detalhes e o spec JSON de uma versão específica do histórico."""
    conexao = db.conectar()
    try:
        resultado = obter_versao_historico_landing_page(conexao, lp_id, version)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao obter versão %s da Landing Page id=%s", version, lp_id)
        return jsonify({"erro": "Falha interna ao consultar versão."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/history/<int:version>/restore", methods=["POST"])
def restaurar_versao_historico_lp(lp_id, version):
    """Restaura o spec de uma versão antiga como a versão atual da Landing Page."""
    conexao = db.conectar()
    try:
        resultado = restaurar_versao_landing_page(conexao, lp_id, version)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao restaurar versão %s da Landing Page id=%s", version, lp_id)
        return jsonify({"erro": "Falha interna ao restaurar versão."}), 500
    finally:
        conexao.close()



@bp.route("/api/landing-pages/<int:lp_id>/archive", methods=["POST"])
def arquivar_lp_endpoint(lp_id):
    """Arquiva uma Landing Page."""
    conexao = db.conectar()
    try:
        resultado = arquivar_lp(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao arquivar Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao arquivar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/publish", methods=["POST"])
def publicar_lp_endpoint(lp_id):
    """Publica a Landing Page externamente."""
    conexao = db.conectar()
    try:
        resultado = publicar_landing_page(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 400
    except Exception:
        logger.exception("Erro ao publicar Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao publicar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/unpublish", methods=["POST"])
def despublicar_lp_endpoint(lp_id):
    """Despublica a Landing Page."""
    conexao = db.conectar()
    try:
        resultado = despublicar_landing_page(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 400
    except Exception:
        logger.exception("Erro ao despublicar Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao despublicar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/republish", methods=["POST"])
def republicar_lp_endpoint(lp_id):
    """Republica a Landing Page com dados atualizados."""
    conexao = db.conectar()
    try:
        resultado = republicar_landing_page(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 400
    except Exception:
        logger.exception("Erro ao republicar Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao republicar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/publication-status", methods=["GET"])
def consultar_status_publicacao_endpoint(lp_id):
    """Consulta o status de publicação e disponibilidade de provider."""
    conexao = db.conectar()
    try:
        resultado = obter_status_publicacao(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao consultar status de publicação id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao consultar status de publicação."}), 500
    finally:
        conexao.close()


@bp.route("/api/public/landing-pages/<slug>", methods=["GET"])
@rate_limit_publico()
def consultar_lp_publica_endpoint(slug):
    """Endpoint público acessível sem autenticação do dashboard, que retorna apenas o payload sanitizado."""
    conexao = db.conectar()
    try:
        resultado = obter_landing_page_publica(conexao, slug)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao consultar Landing Page pública por slug=%s", slug)
        return jsonify({"erro": "Falha interna ao consultar a Landing Page."}), 500
    finally:
        conexao.close()


@bp.route("/api/public/landing-pages/<slug>/events", methods=["POST"])
@rate_limit_publico()
def registrar_evento_endpoint(slug):
    """Endpoint público para rastreamento de visualizações e eventos de conversão."""
    dados = request.get_json(silent=True) or {}
    event_type = dados.get("event_type", "")
    session_id = dados.get("session_id")
    metadata = dados.get("metadata")

    conexao = db.conectar()
    try:
        resultado = registrar_evento_publico_lp(
            conexao, slug=slug, event_type=event_type, session_id=session_id, metadata=metadata
        )
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 400
    except Exception:
        logger.exception("Erro ao registrar evento de analytics para slug=%s", slug)
        return jsonify({"erro": "Falha interna ao registrar evento."}), 500
    finally:
        conexao.close()


@bp.route("/api/landing-pages/<int:lp_id>/analytics", methods=["GET"])
def consultar_analytics_endpoint(lp_id):
    """Retorna métricas agregadas de visualizações e conversões da Landing Page."""
    conexao = db.conectar()
    try:
        resultado = obter_analytics_landing_page(conexao, lp_id)
        return jsonify(resultado), 200
    except ValueError as err:
        return jsonify({"erro": str(err)}), 404
    except Exception:
        logger.exception("Erro ao consultar analytics da Landing Page id=%s", lp_id)
        return jsonify({"erro": "Falha interna ao consultar analytics."}), 500
    finally:
        conexao.close()
