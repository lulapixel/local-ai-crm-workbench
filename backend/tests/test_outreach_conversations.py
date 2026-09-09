"""Testes unitários e de integração do domínio de Histórico de Conversas e Respostas (Outreach Conversations).
"""

import json
import sqlite3
import pytest
from datetime import datetime, timezone

import db
import processar
from outreach.conversations_repository import (
    obter_conversa_por_place_id,
    obter_interacoes_conversa,
)
from outreach.conversations_service import (
    atualizar_interacao_existente,
    excluir_interacao_existente,
    obter_conversa_completa,
    registrar_ligacao,
    registrar_nota_interna,
    registrar_resposta_lead,
    sugerir_resposta_assistida,
)
from outreach.sequences_service import iniciar_sequencia, marcar_etapa_enviada
from outreach.service import salvar_novo_pacote


@pytest.fixture(autouse=True)
def setup_banco_teste(tmp_path, monkeypatch):
    """Redireciona o banco para um arquivo temporário limpo antes de cada teste."""
    caminho_temp = tmp_path / "leads_teste.db"
    monkeypatch.setattr(db, "CAMINHO_BANCO", caminho_temp)

    conexao = sqlite3.connect(caminho_temp)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON;")

    processar.preparar_banco(conexao)

    conexao.commit()
    conexao.close()
    return caminho_temp


def _criar_lead_e_pacote_aprovado(place_id="place_123"):
    conexao = db.conectar()
    agora = datetime.now(timezone.utc).replace(tzinfo=None).isoformat()
    conexao.execute(
        """
        INSERT INTO leads (place_id, nome, categoria, nicho, cidade, nota, num_avaliacoes, status, visto_em)
        VALUES (?, 'Clínica Aurora', 'Saúde', 'odontologia', 'Recife', 4.8, 50, 'novo', ?)
        """,
        (place_id, agora),
    )
    conexao.commit()

    pack = salvar_novo_pacote(
        conexao=conexao,
        place_id=place_id,
        landing_page_id=None,
        strategy={"commercialAngle": "Demonstrativo gratuito", "recommendedCta": "Agendar reunião"},
        messages={
            "initial": "Olá! Gostaria de mostrar um protótipo visual exclusivo.",
            "followups": [
                {"order": 1, "delayDays": 2, "objective": "Verificar leitura", "message": "Oi, conseguiu dar uma olhada?"},
                {"order": 2, "delayDays": 5, "objective": "Reforçar benefício", "message": "Olá! Posso tirar suas dúvidas?"},
                {"order": 3, "delayDays": 9, "objective": "Encerramento", "message": "Vou encerrar por aqui, abraço!"},
            ],
            "closing": "Obrigado!",
        },
        objections=[{"objection": "Já tenho fornecedor", "response": "Trabalhamos de forma complementar"}],
        prototype={"templateKey": "modern", "focus": [], "heroAngle": "", "primaryCta": "", "sectionsToHighlight": []},
        status="approved",
    )
    conexao.close()
    return pack


def test_migracao_idempotente():
    conexao = db.conectar()
    # Executa a migração múltiplas vezes sem lançar erro
    import outreach
    outreach.migrar_outreach(conexao)
    outreach.migrar_outreach(conexao)
    conexao.close()


def test_envio_confirmado_cria_interacao_transacional_com_snapshot():
    pack = _criar_lead_e_pacote_aprovado("place_01")
    seq = iniciar_sequencia(pack["id"], channel="whatsapp")
    step_0 = seq["steps"][0]

    # Confirma envio da etapa inicial (step_order 0)
    marcar_etapa_enviada(step_0["id"])

    conv = obter_conversa_completa("place_01")
    assert conv["status"] == "waiting_lead"
    assert len(conv["interactions"]) == 1

    inter = conv["interactions"][0]
    assert inter["direction"] == "outbound"
    assert inter["interaction_type"] == "message"
    assert inter["channel"] == "whatsapp"
    assert inter["content"] == (step_0.get("message_snapshot") or step_0["message"])
    assert inter["sequence_id"] == seq["id"]
    assert inter["sequence_step_id"] == step_0["id"]


def test_registro_resposta_interrompe_sequencia_e_sugere_proxima_acao():
    pack = _criar_lead_e_pacote_aprovado("place_02")
    seq = iniciar_sequencia(pack["id"])

    # Registra resposta inbound "Gostei, quanto custa?"
    resultado = registrar_resposta_lead(
        place_id="place_02",
        classification="requested_price",
        content="Gostei, quanto custa?",
        channel="whatsapp",
        note="Solicitou proposta até amanhã",
    )

    assert resultado["status"] == "waiting_user"
    assert resultado["next_action_type"] == "send_proposal"

    # Verifica se a sequência foi interrompida com status 'replied'
    conexao = db.conectar()
    linha_seq = conexao.execute("SELECT status, stop_reason FROM outreach_sequences WHERE id = ?", (seq["id"],)).fetchone()
    conexao.close()
    assert linha_seq["status"] == "replied"
    assert linha_seq["stop_reason"] == "replied"

    # Verifica interações gravadas (1 inbound response + 1 nota interna)
    assert len(resultado["interactions"]) == 2
    assert resultado["interactions"][0]["direction"] == "inbound"
    assert resultado["interactions"][0]["classification"] == "requested_price"
    assert resultado["interactions"][1]["direction"] == "internal"
    assert resultado["interactions"][1]["content"] == "Solicitou proposta até amanhã"


def test_classificacao_invalida_lanca_excecao():
    _criar_lead_e_pacote_aprovado("place_03")
    with pytest.raises(ValueError, match="inválida"):
        registrar_resposta_lead(
            place_id="place_03",
            classification="classificacao_inexistente",
            content="Olá",
        )


def test_proximas_acoes_deterministicas():
    pack = _criar_lead_e_pacote_aprovado("place_04")

    conv_won = registrar_resposta_lead("place_04", classification="won", content="Fechamos negócio!")
    assert conv_won["status"] == "won"
    assert conv_won["next_action_type"] == "close_as_won"

    conv_lost = registrar_resposta_lead("place_04", classification="declined", content="Não tenho interesse")
    assert conv_lost["status"] == "lost"
    assert conv_lost["next_action_type"] == "close_as_lost"


def test_notas_internas_e_ligacoes():
    _criar_lead_e_pacote_aprovado("place_05")

    registrar_nota_interna("place_05", "Cliente prefere contato por telefone no fim da tarde.")
    registrar_ligacao("place_05", content="Ligação realizada. Pediu para retornar amanhã.", classification="requested_callback")

    conv = obter_conversa_completa("place_05")
    assert len(conv["interactions"]) == 2
    assert conv["interactions"][0]["interaction_type"] == "note"
    assert conv["interactions"][1]["interaction_type"] == "call"


def test_edicao_e_restricao_de_exclusao_de_interacoes():
    pack = _criar_lead_e_pacote_aprovado("place_06")
    seq = iniciar_sequencia(pack["id"])
    step_0 = seq["steps"][0]
    marcar_etapa_enviada(step_0["id"])

    conv = registrar_resposta_lead("place_06", classification="interested", content="Tenho interesse")
    inter_outbound = conv["interactions"][0]
    inter_inbound = conv["interactions"][1]

    # Mensagem enviada automaticamente pela sequência NÃO pode ser excluída
    with pytest.raises(ValueError, match="automáticas não podem ser apagadas"):
        excluir_interacao_existente(inter_outbound["id"])

    # Edição de classificação em resposta manual
    atualizada = atualizar_interacao_existente(inter_inbound["id"], classification="requested_price")
    assert atualizada["next_action_type"] == "send_proposal"

    # Exclusão de resposta manual permitida
    excluir_interacao_existente(inter_inbound["id"])
    conv_pos_del = obter_conversa_completa("place_06")
    assert len(conv_pos_del["interactions"]) == 1


def test_sugestao_resposta_ia_com_fallback():
    _criar_lead_e_pacote_aprovado("place_07")
    conv = registrar_resposta_lead("place_07", classification="requested_price", content="Quanto custa?")
    inter_inbound = [i for i in conv["interactions"] if i["direction"] == "inbound"][0]

    sugestao = sugerir_resposta_assistida(inter_inbound["id"])
    assert sugestao["interaction_id"] == inter_inbound["id"]
    assert "suggested_reply" in sugestao
    assert len(sugestao["suggested_reply"]) > 5


def test_exclusao_em_cascata_lead():
    _criar_lead_e_pacote_aprovado("place_08")
    registrar_nota_interna("place_08", "Teste de nota")

    conexao = db.conectar()
    conexao.execute("DELETE FROM leads WHERE place_id = 'place_08'")
    conexao.commit()

    conv = obter_conversa_por_place_id(conexao, "place_08")
    assert conv is None
    conexao.close()
