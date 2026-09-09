"""Módulo de Outreach (Pacote de Conversão) do ProspectOS.

Gerencia o diagnóstico comercial determinístico, geração de copy unificada por IA/fallback,
versões do pacote, transações com Landing Pages e rotas REST.
"""

from outreach.repository import (
    alterar_status_pacote,
    atualizar_pacote,
    obter_por_id,
    obter_por_place_id,
    obter_versoes_pacote,
    salvar_novo_pacote,
)
from outreach.routes import bp
from outreach.schema import (
    INDICES_CONVERSION_PACKS_SQL,
    INDICES_CONVERSION_PACK_VERSIONS_SQL,
    TABELA_CONVERSION_PACKS_SQL,
    TABELA_CONVERSION_PACK_VERSIONS_SQL,
    migrar_outreach,
)
from outreach.service import (
    aprovar_pacote_conversao,
    arquivar_pacote_conversao,
    atualizar_pacote_manualmente,
    obter_ou_gerar_pacote,
    obter_pacote_por_place_id,
    regenerar_secoes_pacote,
)
from outreach.strategy import extrair_evidencias_e_estrategia

__all__ = [
    "bp",
    "migrar_outreach",
    "extrair_evidencias_e_estrategia",
    "obter_ou_gerar_pacote",
    "obter_pacote_por_place_id",
    "atualizar_pacote_manualmente",
    "regenerar_secoes_pacote",
    "aprovar_pacote_conversao",
    "arquivar_pacote_conversao",
    "obter_por_place_id",
    "obter_por_id",
    "obter_versoes_pacote",
    "salvar_novo_pacote",
    "atualizar_pacote",
    "alterar_status_pacote",
    "TABELA_CONVERSION_PACKS_SQL",
    "TABELA_CONVERSION_PACK_VERSIONS_SQL",
    "INDICES_CONVERSION_PACKS_SQL",
    "INDICES_CONVERSION_PACK_VERSIONS_SQL",
]
