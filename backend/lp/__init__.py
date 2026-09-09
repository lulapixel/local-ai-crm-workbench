"""Módulo do domínio de Landing Pages (LP) do ProspectOS.

Gerencia o catálogo de templates, geração de copy por IA/fallback determinístico,
validação de JSON de spec, rotas REST e persistência no SQLite.
"""

from .copywriter import extrair_fatos_deterministicos, gerar_lp_content, gerar_spec_fallback
from .repository import (
    arquivar_landing_page,
    atualizar_landing_page,
    criar_landing_page,
    obter_por_id,
    obter_por_place_id,
    obter_por_slug,
    salvar_historico_brief,
    slug_existe,
)
from .routes import bp
from .schema import (
    INDICES_LANDING_PAGES_SQL,
    INDICES_LP_BRIEFS_SQL,
    TABELA_LANDING_PAGES_SQL,
    TABELA_LP_BRIEFS_SQL,
    migrar_landing_pages,
    migrar_lp,
    migrar_lp_briefs,
)
from .service import (
    formatar_resposta_lp,
    gerar_slug_unico,
    obter_landing_page_por_place_id,
    obter_landing_page_por_slug,
    obter_ou_criar_landing_page,
    regenerar_conteudo_lp,
)
from .template_catalog import TEMPLATES, selecionar_template
from .validators import validar_e_sanitizar_spec

__all__ = [
    "TABELA_LP_BRIEFS_SQL",
    "TABELA_LANDING_PAGES_SQL",
    "INDICES_LP_BRIEFS_SQL",
    "INDICES_LANDING_PAGES_SQL",
    "migrar_lp",
    "migrar_lp_briefs",
    "migrar_landing_pages",
    "TEMPLATES",
    "selecionar_template",
    "extrair_fatos_deterministicos",
    "gerar_spec_fallback",
    "gerar_lp_content",
    "validar_e_sanitizar_spec",
    "obter_por_place_id",
    "obter_por_slug",
    "obter_por_id",
    "criar_landing_page",
    "atualizar_landing_page",
    "arquivar_landing_page",
    "salvar_historico_brief",
    "slug_existe",
    "gerar_slug_unico",
    "formatar_resposta_lp",
    "obter_ou_criar_landing_page",
    "obter_landing_page_por_place_id",
    "obter_landing_page_por_slug",
    "regenerar_conteudo_lp",
    "bp",
]