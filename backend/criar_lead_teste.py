"""Cria, atualiza ou remove um lead de teste apontando para o SEU próprio número.

Permite exercitar a prospecção e as integrações de conversa/outreach sem risco
de enviar mensagens para um cliente real.

Uso:
    py criar_lead_teste.py 65999998888                   (cria/atualiza lead de teste)
    py criar_lead_teste.py 65999998888 --cidade "São Paulo"
    py criar_lead_teste.py --remover                     (remove o lead de teste)

Opções adicionais:
    --installed   Força a alteração no banco do APP INSTALADO (%APPDATA%\\ProspectOS\\leads.db)
    --local       Força a alteração no banco do AMBIENTE LOCAL (pasta do projeto)
    --dry-run     Modo de simulação sem escrita (exibe banco, dados e tabelas afetadas)
"""

import os
import re
import sqlite3
import sys
from datetime import datetime
from pathlib import Path

from paths import DIR_DADOS

PLACE_ID = "TESTE-MEU-NUMERO"


def resolver_caminho_banco(forcador_instalado=False, forcador_local=False):
    """Resolve o banco de dados a ser utilizado conforme as flags informadas.
    Retorna tuple: (caminho_path, origem_str)
    """
    instalado = Path(os.environ.get("APPDATA", "")) / "ProspectOS" / "leads.db"
    local = DIR_DADOS / "leads.db"

    if forcador_instalado and forcador_local:
        print("Erro: Não é possível especificar --installed e --local simultaneamente.")
        sys.exit(1)

    if forcador_instalado:
        return instalado, "INSTALADO (--installed)"
    if forcador_local:
        return local, "LOCAL (--local)"

    # Se nenhuma opção foi fornecida: detecta se o instalado existe
    if instalado.exists():
        return instalado, "INSTALADO (detectado automaticamente)"
    return local, "LOCAL (detectado automaticamente)"


def normalizar_telefone(telefone_bruto):
    digitos = re.sub(r"\D", "", telefone_bruto or "")
    if digitos.startswith("55") and len(digitos) in (12, 13):
        digitos = digitos[2:]
    return digitos


def buscar_leads_por_telefone(conexao, telefone_digitos):
    """Busca no banco leads que possuem o mesmo número de telefone normalizado,
    ignorando o próprio lead de teste.
    """
    if not telefone_digitos:
        return []

    linhas = conexao.execute(
        "SELECT place_id, nome, cidade, telefone FROM leads WHERE place_id != ?",
        (PLACE_ID,),
    ).fetchall()

    encontrados = []
    for linha in linhas:
        tel_norm = normalizar_telefone(linha[3])
        if tel_norm and tel_norm == telefone_digitos:
            encontrados.append(dict(linha))

    return encontrados


def relatar_registros_relacionados(conexao, place_id):
    """Mapeia os registros dependentes existentes para o place_id informado."""
    relatorio = {}

    relatorio["historico_status"] = conexao.execute(
        "SELECT COUNT(*) FROM historico_status WHERE place_id = ?", (place_id,)
    ).fetchone()[0]

    relatorio["conversion_packs"] = conexao.execute(
        "SELECT COUNT(*) FROM conversion_packs WHERE place_id = ?", (place_id,)
    ).fetchone()[0]

    relatorio["conversion_pack_versions"] = conexao.execute(
        """
        SELECT COUNT(*) FROM conversion_pack_versions
        WHERE conversion_pack_id IN (SELECT id FROM conversion_packs WHERE place_id = ?)
        """,
        (place_id,),
    ).fetchone()[0]

    relatorio["outreach_sequences"] = conexao.execute(
        "SELECT COUNT(*) FROM outreach_sequences WHERE place_id = ?", (place_id,)
    ).fetchone()[0]

    relatorio["outreach_sequence_steps"] = conexao.execute(
        """
        SELECT COUNT(*) FROM outreach_sequence_steps
        WHERE sequence_id IN (SELECT id FROM outreach_sequences WHERE place_id = ?)
        """,
        (place_id,),
    ).fetchone()[0]

    relatorio["outreach_conversations"] = conexao.execute(
        "SELECT COUNT(*) FROM outreach_conversations WHERE place_id = ?", (place_id,)
    ).fetchone()[0]

    relatorio["outreach_interactions"] = conexao.execute(
        """
        SELECT COUNT(*) FROM outreach_interactions
        WHERE conversation_id IN (SELECT id FROM outreach_conversations WHERE place_id = ?)
        """,
        (place_id,),
    ).fetchone()[0]

    # tabelas opcionais de landing pages
    for tab in ("landing_pages", "lp_briefs"):
        try:
            relatorio[tab] = conexao.execute(
                f"SELECT COUNT(*) FROM {tab} WHERE place_id = ?", (place_id,)
            ).fetchone()[0]
        except sqlite3.OperationalError:
            relatorio[tab] = 0

    return relatorio


def remover(caminho_banco, dry_run=False, auto_confirm=False):
    """Remove estritamente o lead de teste (TESTE-MEU-NUMERO) e todos os seus
    registros vinculados nas tabelas de Outreach e LP em ordem correta e transacional.
    """
    if not caminho_banco.exists():
        print(f"Banco não encontrado em: {caminho_banco}")
        return

    conexao = sqlite3.connect(caminho_banco)
    try:
        conexao.row_factory = sqlite3.Row
        lead = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (PLACE_ID,)).fetchone()
        if not lead:
            print(f"Não há lead de teste com ID '{PLACE_ID}' para remover.")
            return

        relatorio = relatar_registros_relacionados(conexao, PLACE_ID)

        if dry_run:
            print("\n=== SIMULAÇÃO DE REMOÇÃO (--dry-run) ===")
            print(f"Banco: {caminho_banco}")
            print(f"Lead a remover: {dict(lead)}")
            print("Registros relacionados que seriam excluídos:")
            for tab, qtd in relatorio.items():
                if qtd > 0:
                    print(f"  - {tab}: {qtd} registro(s)")
            print("Tabelas afetadas: leads, historico_status e todas as dependentes de Outreach/LP.")
            print("Nenhuma alteração foi realizada (modo simulação).")
            return

        if not auto_confirm:
            print(f"\nLead de teste localizado: '{lead['nome']}' ({lead['telefone']})")
            print("Registros relacionados encontrados:")
            for tab, qtd in relatorio.items():
                if qtd > 0:
                    print(f"  - {tab}: {qtd} registro(s)")
            resp = input(f"Confirmar remoção DEFINITIVA do lead '{PLACE_ID}'? [s/N]: ").strip().lower()
            if resp != "s":
                print("Operação cancelada pelo usuário.")
                return

        # Execução da remoção dentro de uma única transação atômica
        with conexao:
            # 1. Outreach steps
            conexao.execute(
                """
                DELETE FROM outreach_sequence_steps
                WHERE sequence_id IN (SELECT id FROM outreach_sequences WHERE place_id = ?)
                """,
                (PLACE_ID,),
            )
            # 2. Outreach sequences
            conexao.execute("DELETE FROM outreach_sequences WHERE place_id = ?", (PLACE_ID,))
            # 3. Outreach interactions
            conexao.execute(
                """
                DELETE FROM outreach_interactions
                WHERE conversation_id IN (SELECT id FROM outreach_conversations WHERE place_id = ?)
                """,
                (PLACE_ID,),
            )
            # 4. Outreach conversations
            conexao.execute("DELETE FROM outreach_conversations WHERE place_id = ?", (PLACE_ID,))
            # 5. Conversion pack versions
            conexao.execute(
                """
                DELETE FROM conversion_pack_versions
                WHERE conversion_pack_id IN (SELECT id FROM conversion_packs WHERE place_id = ?)
                """,
                (PLACE_ID,),
            )
            # 6. Conversion packs
            conexao.execute("DELETE FROM conversion_packs WHERE place_id = ?", (PLACE_ID,))
            # 7. Landing page events & pages (se existirem)
            try:
                conexao.execute(
                    """
                    DELETE FROM landing_page_events
                    WHERE landing_page_id IN (SELECT id FROM landing_pages WHERE place_id = ?)
                    """,
                    (PLACE_ID,),
                )
                conexao.execute("DELETE FROM landing_pages WHERE place_id = ?", (PLACE_ID,))
                conexao.execute("DELETE FROM lp_briefs WHERE place_id = ?", (PLACE_ID,))
            except sqlite3.OperationalError:
                pass
            # 8. Histórico de status
            conexao.execute("DELETE FROM historico_status WHERE place_id = ?", (PLACE_ID,))
            # 9. Tabela principal de leads
            conexao.execute("DELETE FROM leads WHERE place_id = ?", (PLACE_ID,))

        print(f"Lead de teste '{PLACE_ID}' e todos os registros relacionados foram removidos com sucesso.")

    finally:
        conexao.close()


def criar_ou_atualizar(caminho_banco, telefone_bruto, cidade="Não informada", dry_run=False, auto_confirm=False):
    """Cria ou atualiza o lead de teste estritamente sob a chave TESTE-MEU-NUMERO."""
    digitos = normalizar_telefone(telefone_bruto)
    if len(digitos) not in (10, 11):
        print(f"Erro: Número inválido '{telefone_bruto}'. Use DDD + número de 10 ou 11 dígitos.")
        sys.exit(1)

    caminho_banco.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(caminho_banco)
    try:
        conexao.row_factory = sqlite3.Row

        # Verifica se o telefone informado já pertence a outros leads no banco
        outros_leads = buscar_leads_por_telefone(conexao, digitos)
        if outros_leads:
            print(f"\n[ALERTA] O telefone {digitos} já está cadastrado nos seguintes leads existentes:")
            for item in outros_leads:
                print(f"  - [{item['place_id']}] {item['nome']} (Cidade: {item['cidade'] or 'N/A'})")
            print("O script NÃO removerá nem alterará nenhum desses leads existentes.")
            if not dry_run and not auto_confirm:
                resp = input("Deseja continuar criando/atualizando apenas o lead de teste? [s/N]: ").strip().lower()
                if resp != "s":
                    print("Operação cancelada.")
                    return

        lead_existente = conexao.execute("SELECT * FROM leads WHERE place_id = ?", (PLACE_ID,)).fetchone()
        acao_str = "ATUALIZAR" if lead_existente else "CRIAR"

        agora = datetime.now().isoformat(timespec="seconds")
        dados_lead = {
            "place_id": PLACE_ID,
            "nome": "TESTE - Meu próprio número",
            "categoria": "Teste do cockpit",
            "endereco": "Sem endereço",
            "nota": 5.0,
            "num_avaliacoes": 100,
            "telefone": digitos,
            "whatsapp_link": f"https://wa.me/55{digitos}",
            "nicho": "teste",
            "cidade": cidade or "Não informada",
            "site_status": "sem_site",
            "site_problemas": None,
            "status": "novo",
            "visto_em": agora,
            "atualizado_em": agora,
        }

        if dry_run:
            print("\n=== SIMULAÇÃO DE ESCRITA (--dry-run) ===")
            print(f"Banco: {caminho_banco}")
            print(f"Ação: {acao_str} lead com place_id '{PLACE_ID}'")
            print(f"Dados a gravar: {dados_lead}")
            print("Tabelas afetadas: leads")
            print("Nenhuma alteração foi realizada (modo simulação).")
            return

        if not auto_confirm:
            print(f"\nSerá realizado: {acao_str} lead de teste '{PLACE_ID}'")
            print(f"Banco: {caminho_banco}")
            print(f"Telefone: {digitos} | Cidade: {cidade or 'Não informada'}")
            resp = input("Confirmar operação de escrita? [s/N]: ").strip().lower()
            if resp != "s":
                print("Operação cancelada pelo usuário.")
                return

        with conexao:
            conexao.execute(
                """
                INSERT INTO leads (place_id, nome, categoria, endereco, nota, num_avaliacoes,
                                   telefone, whatsapp_link, nicho, cidade, site_status,
                                   site_problemas, status, visto_em, atualizado_em)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(place_id) DO UPDATE SET
                    nome = excluded.nome,
                    telefone = excluded.telefone,
                    whatsapp_link = excluded.whatsapp_link,
                    cidade = excluded.cidade,
                    atualizado_em = excluded.atualizado_em
                """,
                (
                    dados_lead["place_id"],
                    dados_lead["nome"],
                    dados_lead["categoria"],
                    dados_lead["endereco"],
                    dados_lead["nota"],
                    dados_lead["num_avaliacoes"],
                    dados_lead["telefone"],
                    dados_lead["whatsapp_link"],
                    dados_lead["nicho"],
                    dados_lead["cidade"],
                    dados_lead["site_status"],
                    dados_lead["site_problemas"],
                    dados_lead["status"],
                    dados_lead["visto_em"],
                    dados_lead["atualizado_em"],
                ),
            )

        print(f"\nSucesso: Lead de teste '{PLACE_ID}' {acao_str.lower()}do com o número {digitos}.")
        print(f"Banco modificado: {caminho_banco}")

    finally:
        conexao.close()


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print(__doc__)
        sys.exit(0)

    dry_run = "--dry-run" in args
    forcador_instalado = "--installed" in args
    forcador_local = "--local" in args
    auto_confirm = "--sim" in args or "-y" in args

    # Filtra flags dos argumentos posicionais
    args_posicionais = [
        a for a in args
        if not a.startswith("--") and a not in ("-y",)
    ]

    caminho_banco, origem_banco = resolver_caminho_banco(forcador_instalado, forcador_local)
    print(f"Banco selecionado: {caminho_banco} [{origem_banco}]")

    # Checa se é comando de remoção
    if "--remover" in args:
        remover(caminho_banco, dry_run=dry_run, auto_confirm=auto_confirm)
        return

    # Extrai cidade opcional se passada via --cidade "Cidade"
    cidade = "Não informada"
    if "--cidade" in args:
        try:
            idx = args.index("--cidade")
            if idx + 1 < len(args):
                cidade = args[idx + 1]
        except ValueError:
            pass

    if not args_posicionais:
        print("Erro: Informe o número de telefone (ex: py criar_lead_teste.py 65999998888)")
        sys.exit(1)

    telefone = args_posicionais[0]
    criar_ou_atualizar(caminho_banco, telefone, cidade=cidade, dry_run=dry_run, auto_confirm=auto_confirm)


if __name__ == "__main__":
    main()
