"""Exportação controlada do contexto do ProspectOS para um vault Obsidian.

O CRM/SQLite continua sendo a fonte de verdade. Este módulo só cria ou atualiza
notas gerenciadas pelo ProspectOS no vault, sempre em uma direção:
ProspectOS -> Obsidian.

Por segurança, a CLI exige ``--write`` para tocar no vault. Arquivos existentes
que não foram criados por este módulo nunca são sobrescritos automaticamente.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
import unicodedata
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional


SCHEMA_VERSION = "prospectos-obsidian-sync/v1"
MANAGED_MARKER = "managed_by: prospectos-obsidian-sync:v1"
MANAGED_ID = "prospectos-obsidian-sync:v1"
PROJECT_RELATIVE = Path("02-Projects") / "prospectos"
LEADS_RELATIVE = PROJECT_RELATIVE / "leads"


class ObsidianSyncError(RuntimeError):
    """Erro recuperável de validação ou conflito no vault."""


@dataclass(frozen=True)
class SyncItem:
    path: Path
    status: str
    reason: str = ""


def _agora_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _yaml_scalar(value: Any) -> str:
    """Serializa um escalar sem depender de PyYAML."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def _frontmatter(fields: Mapping[str, Any]) -> str:
    linhas = ["---"]
    for chave, valor in fields.items():
        if isinstance(valor, (list, tuple)):
            itens = ", ".join(_yaml_scalar(item) for item in valor)
            linhas.append(f"{chave}: [{itens}]")
        else:
            linhas.append(f"{chave}: {_yaml_scalar(valor)}")
    linhas.extend(["---", ""])
    return "\n".join(linhas)


def safe_slug(value: Any, fallback: str = "sem-identificador") -> str:
    """Cria um nome de arquivo previsível sem permitir traversal ou separadores."""
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:100] or fallback


def _texto_limitado(value: Any, limite: int = 4000) -> str:
    texto = str(value or "").strip()
    return texto[:limite]


def _lista_textos(value: Any, limite: int = 12) -> list[str]:
    if not isinstance(value, (list, tuple)):
        return []
    return [_texto_limitado(item, 500) for item in value[:limite] if str(item or "").strip()]


def _dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _unwrap_context(raw: Mapping[str, Any]) -> Dict[str, Any]:
    data = raw.get("data")
    return _dict(data) if isinstance(data, Mapping) else dict(raw)


def _public_lead(lead: Mapping[str, Any]) -> Dict[str, Any]:
    """Allowlist do que pode sair do CRM e virar nota local."""
    aliases = {
        "place_id": ("place_id", "placeId", "id"),
        "name": ("name", "nome", "empresa", "business_name"),
        "category": ("category", "categoria", "nicho"),
        "city": ("city", "cidade"),
        "address": ("address", "endereco"),
        "phone": ("phone", "telefone"),
        "website": ("website", "site", "url"),
        "status": ("status", "estagio", "stage"),
        "score": ("score", "pontuacao"),
        "site_status": ("site_status", "situacao_site", "status_site"),
        "instagram": ("instagram", "instagram_username", "username"),
        "whatsapp_link": ("whatsapp_link", "whatsapp"),
        "instagram_url": ("instagram_url",),
        "rating": ("rating", "nota"),
        "review_count": ("review_count", "num_avaliacoes"),
        "observations": ("observations", "observacoes"),
        "updated_at": ("updated_at", "atualizado_em", "updatedAt"),
    }
    clean: Dict[str, Any] = {}
    for target, keys in aliases.items():
        for key in keys:
            if key in lead and lead[key] not in (None, "", []):
                clean[target] = _texto_limitado(lead[key])
                break
    return clean


def _public_pack(pack: Mapping[str, Any]) -> Dict[str, Any]:
    messages = _dict(pack.get("messages"))
    followups = messages.get("followups")
    clean_followups = []
    if isinstance(followups, list):
        for item in followups[:3]:
            row = _dict(item)
            clean_followups.append(
                {
                    "objective": _texto_limitado(row.get("objective"), 300),
                    "message": _texto_limitado(row.get("message"), 1200),
                }
            )
    result: Dict[str, Any] = {}
    for target, key in (("status", "status"), ("version", "version")):
        if pack.get(key) not in (None, "", []):
            result[target] = _texto_limitado(pack[key], 1000)
    strategy = pack.get("strategy")
    if isinstance(strategy, Mapping):
        clean_strategy: Dict[str, Any] = {}
        for key in (
            "opportunity",
            "problem",
            "evidence",
            "commercialAngle",
            "recommendedCta",
            "confidence",
            "primaryRule",
        ):
            if strategy.get(key) not in (None, "", []):
                value = strategy[key]
                clean_strategy[key] = _lista_textos(value, 12) if isinstance(value, list) else _texto_limitado(value, 1000)
        if clean_strategy:
            result["strategy"] = clean_strategy
    elif strategy not in (None, "", []):
        result["strategy"] = _texto_limitado(strategy, 1000)
    if messages.get("initial"):
        result["initial_message"] = _texto_limitado(messages["initial"], 1200)
    if clean_followups:
        result["followups"] = clean_followups
    if pack.get("objections"):
        result["objections"] = _lista_textos(pack["objections"])
    return result


def _public_lp(page: Mapping[str, Any]) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for target, keys in {
        "slug": ("slug",),
        "status": ("status",),
        "public_url": ("public_url", "publicUrl"),
        "template": ("template_key", "template", "templateKey"),
        "schema_version": ("schema_version", "schemaVersion"),
        "publish_provider": ("publish_provider", "publishProvider"),
    }.items():
        for key in keys:
            if page.get(key) not in (None, "", []):
                result[target] = _texto_limitado(page[key], 1000)
                break
    return result


def normalize_context(raw: Mapping[str, Any]) -> Dict[str, Any]:
    """Normaliza o envelope do MCP sem copiar campos desconhecidos ou secretos."""
    context = _unwrap_context(raw)
    lead_raw = _dict(context.get("lead"))
    # O contrato site-opportunity/v1 já entrega dados sanitizados em blocos
    # semânticos (company/crm/current_website/contact), em vez de expor o lead
    # bruto. Recompõe somente os campos públicos necessários para a nota.
    if not lead_raw and any(key in context for key in ("company", "crm", "current_website", "contact")):
        company = _dict(context.get("company"))
        crm = _dict(context.get("crm"))
        website = _dict(context.get("current_website"))
        contact = _dict(context.get("contact"))
        reputation = _dict(context.get("reputation"))
        lead_raw = {
            "place_id": context.get("place_id"),
            "name": company.get("name"),
            "category": company.get("category") or company.get("niche"),
            "city": company.get("city"),
            "address": company.get("address"),
            "status": crm.get("status"),
            "score": crm.get("score"),
            "site_status": website.get("status"),
            "website": website.get("url"),
            "phone": contact.get("phone"),
            "whatsapp_link": contact.get("whatsapp_link"),
            "instagram_url": contact.get("instagram_url"),
            "rating": reputation.get("rating"),
            "review_count": reputation.get("review_count"),
        }
    lead = _public_lead(lead_raw)
    pack = _public_pack(_dict(context.get("conversion_pack")))
    page = _public_lp(_dict(context.get("landing_page")))
    investment_raw = _dict(context.get("investment"))
    investment = {
        "eligible": bool(investment_raw.get("eligible", False)),
        "level": _texto_limitado(investment_raw.get("level"), 50),
        "blockers": _lista_textos(investment_raw.get("blockers"), 10),
    }
    handoff_raw = _dict(context.get("handoff"))
    handoff = {
        "prospectos_owns": _lista_textos(handoff_raw.get("prospectos_owns"), 12),
        "sol_advisor_owns": _lista_textos(handoff_raw.get("sol_advisor_owns"), 12),
    }
    lead_id = lead.get("place_id") or lead.get("name") or context.get("place_id") or "sem-identificador"
    return {
        "contract_version": _texto_limitado(context.get("contract_version"), 80),
        "lead": lead,
        "conversion_pack": pack,
        "landing_page": page,
        "investment": investment,
        "handoff": handoff,
        "lead_id": _texto_limitado(lead_id, 160),
    }


def _validate_vault(vault: Path) -> Path:
    vault = vault.expanduser().resolve()
    if not vault.is_dir():
        raise ObsidianSyncError(f"Vault Obsidian inexistente: {vault}")
    for required in (".obsidian", "02-Projects"):
        if not (vault / required).is_dir():
            raise ObsidianSyncError(f"O vault não possui a pasta obrigatória '{required}': {vault}")
    return vault


def _inside(root: Path, target: Path) -> bool:
    try:
        target.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                # Não mascarar a falha de escrita/substituição por uma falha
                # secundária de limpeza do temporário.
                pass


def _is_managed(content: str) -> bool:
    return any(
        marker in content
        for marker in (
            MANAGED_MARKER,
            f'managed_by: "{MANAGED_ID}"',
            f'"managed_by": "{MANAGED_ID}"',
        )
    )


def _write_managed(path: Path, content: str, *, write: bool, force: bool = False) -> SyncItem:
    if path.exists():
        current = path.read_text(encoding="utf-8")
        if current == content:
            return SyncItem(path, "unchanged")
        if not _is_managed(current) and not force:
            return SyncItem(path, "conflict", "arquivo existente não gerenciado")
        if not write:
            return SyncItem(path, "would_update")
        _atomic_write(path, content)
        return SyncItem(path, "updated")
    if not write:
        return SyncItem(path, "would_create")
    _atomic_write(path, content)
    return SyncItem(path, "created")


def _project_notes(repo: Path, updated: str) -> Dict[str, str]:
    repo_uri = repo.resolve().as_uri()
    analysis_uri = (repo / "docs" / "codex" / "ProspectOS-Mecanismos-Aderencia-Analysis.md").resolve().as_uri()
    mcp_uri = (repo / "docs" / "MCP.md").resolve().as_uri()
    report_uri = (repo / "graphify-out" / "GRAPH_REPORT.md").resolve().as_uri()
    common = _frontmatter(
        {
            "type": "project",
            "status": "active",
            "priority": "high",
            "phase": "integration",
            "agent": "codex",
            "repo": str(repo.resolve()),
            "updated": updated[:10],
            "managed_by": "prospectos-obsidian-sync:v1",
        }
    )
    project = common + """# ProspectOS\n\n## Identidade\n\nCRM de prospecção e produção assistida de Landing Pages para pequenos negócios locais. O ProspectOS mantém o contexto comercial, o CRM, o conversion pack e a demonstração da LP.\n\n## Objetivo\n\nUsar o vault como camada durável de contexto, decisões e handoffs, sem duplicar o banco operacional.\n\n## Limites\n\n- O CRM/SQLite é a fonte de verdade dos leads e das sequências.\n- A sincronização desta integração é somente `ProspectOS -> Obsidian`.\n- Nenhuma nota inicia contato, altera funil, publica site ou contém credenciais.\n- O Sol Advisor permanece responsável pela produção, revisão e evidência do site.\n\n## Referências\n\n- [Repositório](""" + repo_uri + ")\n- [Análise de mecanismos](""" + analysis_uri + ")\n- [Contrato MCP](""" + mcp_uri + ")\n- [Relatório estrutural](""" + report_uri + ")\n"
    status = _frontmatter(
        {
            "type": "status",
            "status": "active",
            "project": "prospectos",
            "updated": updated[:10],
            "managed_by": "prospectos-obsidian-sync:v1",
        }
    ) + """# Status\n\n## Estado atual\n\n- Projeto ProspectOS criado no Codex e conteúdo anterior transferido.\n- Mecanismos existentes analisados com prioridade para reuso.\n- Integração com este vault criada como exportação unidirecional e idempotente.\n- A configuração `prospectos` foi persistida com interpretador Python absoluto que possui Flask/MCP e aponta para o backend e o vault; a enumeração pelo CLI legado continua inconclusiva por incompatibilidade de versão.\n- O runtime MCP deste checkout foi validado por stdio: contexto real `site-opportunity/v1` lido para `GAP Barber & Studio` e nota exportada em `02-Projects/prospectos/leads/`.\n- A repetição do mesmo export retornou `unchanged`/`idempotent=true`; o CRM permaneceu sem mutação.\n\n## Prova disponível\n\n- Health HTTP local respondeu `200` com `database_ready=true`.\n- Contratos `site-opportunity/v1` e `site-result/v1`.\n- Gates `demo`/`full` com aprovação humana.\n- Preview local `/demos/<slug>` reutilizável.\n- Nota Obsidian sanitizada com allowlist e marcador `managed_by`.\n- Suíte completa do backend: 439 testes passaram no ambiente instalado.\n\n## Lacunas\n\n- O CLI legado não consegue carregar a configuração atual do aplicativo; a prova disponível é o runtime stdio direto, não a enumeração nativa pela versão antiga.\n- Publisher remoto ainda não prova deploy real.\n- Permanecem warnings preexistentes de depreciação e do stack MCP/Pydantic; não bloqueiam esta integração.\n"""
    next_note = _frontmatter(
        {
            "type": "next",
            "status": "active",
            "project": "prospectos",
            "updated": updated[:10],
            "managed_by": "prospectos-obsidian-sync:v1",
        }
    ) + """# Next\n\n1. Revisar no Obsidian a nota de `GAP Barber & Studio` e registrar apenas observações humanas, se necessário.\n2. Revisar o preview local da Landing Page com o contrato `site-opportunity/v1`; não publicar nem contatar o lead neste gate.\n3. Se houver aprovação humana, registrar somente o resultado comprovado via `registrar_resultado_site`; manter a operação idempotente.\n4. Repetir o export para um segundo lead apenas depois de fechar a revisão do primeiro.\n5. Só então avaliar uma tool de estado de sequência em modo somente leitura.\n"""
    contract = _frontmatter(
        {
            "type": "integration",
            "status": "active",
            "project": "prospectos",
            "updated": updated[:10],
            "managed_by": "prospectos-obsidian-sync:v1",
        }
    ) + """# ProspectOS ↔ Obsidian\n\n## Direção\n\n`ProspectOS -> Obsidian` por exportação explícita. O Obsidian não escreve automaticamente no CRM.\n\n## Dados permitidos\n\nContexto público do lead, score/status, conversion pack, estado da Landing Page, blockers de investimento e responsabilidades do handoff.\n\n## Dados proibidos\n\nChaves de API, tokens, senhas, cookies, sessões do Instagram, banco SQLite bruto e dumps não sanitizados.\n\n## Idempotência\n\nNotas gerenciadas carregam o marcador `managed_by: prospectos-obsidian-sync:v1`. Arquivos existentes sem esse marcador não são sobrescritos.\n\n## Fonte de verdade\n\n- Leads, CRM e sequências: ProspectOS.\n- Decisões, contexto persistente e handoffs: Obsidian.\n- Produção e revisão de site: Sol Advisor.\n"""
    return {
        "PROJECT.md": project,
        "STATUS.md": status,
        "NEXT.md": next_note,
        "OBSIDIAN-SYNC.md": contract,
    }


def export_project(
    vault_path: Path,
    repo_path: Optional[Path] = None,
    *,
    write: bool = False,
    force: bool = False,
    updated: Optional[str] = None,
) -> Dict[str, Any]:
    """Cria/atualiza a nota do projeto ProspectOS no vault."""
    vault = _validate_vault(vault_path)
    repo = (repo_path or Path(__file__).resolve().parents[1]).resolve()
    project_dir = (vault / PROJECT_RELATIVE).resolve()
    if not _inside(vault, project_dir):
        raise ObsidianSyncError("Destino do projeto saiu da raiz do vault.")
    timestamp = updated or _agora_iso()
    items = []
    if write:
        project_dir.mkdir(parents=True, exist_ok=True)
    for name, content in _project_notes(repo, timestamp).items():
        items.append(_write_managed(project_dir / name, content, write=write, force=force))
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "source": "ProspectOS",
        "source_repo": str(repo),
        "generated_at": timestamp,
        "sync_direction": "prospectos_to_obsidian",
        "managed_by": MANAGED_ID,
        "files": [item.path.name for item in items],
    }
    manifest_content = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    manifest_item = _write_managed(project_dir / ".prospectos-sync.json", manifest_content, write=write, force=force)
    items.append(manifest_item)
    return {
        "vault": str(vault),
        "project_dir": str(project_dir),
        "write": write,
        "items": [
            {"path": str(item.path), "status": item.status, "reason": item.reason}
            for item in items
        ],
    }


def export_lead(
    vault_path: Path,
    raw_context: Mapping[str, Any],
    *,
    write: bool = False,
    force: bool = False,
    updated: Optional[str] = None,
) -> Dict[str, Any]:
    """Exporta um contexto ``site-opportunity/v1`` sanitizado para uma nota."""
    vault = _validate_vault(vault_path)
    clean = normalize_context(raw_context)
    lead = clean["lead"]
    slug = safe_slug(clean["lead_id"])
    target_dir = (vault / LEADS_RELATIVE).resolve()
    if not _inside(vault, target_dir):
        raise ObsidianSyncError("Destino das notas de lead saiu da raiz do vault.")
    timestamp = updated or _agora_iso()
    front = _frontmatter(
        {
            "type": "prospect",
            "status": lead.get("status", "unknown"),
            "project": "prospectos",
            "source": "prospectos",
            "source_id": clean["lead_id"],
            "site_status": lead.get("site_status", "unknown"),
            "updated": timestamp[:10],
            "sync_direction": "prospectos_to_obsidian",
            "managed_by": "prospectos-obsidian-sync:v1",
            "contract_version": clean.get("contract_version") or "unknown",
        }
    )
    lines = [front, f"# {lead.get('name', clean['lead_id'])}", "", "## Lead público", ""]
    labels = {
        "category": "Categoria",
        "city": "Cidade",
        "address": "Endereço",
        "phone": "Telefone",
        "website": "Site",
        "instagram": "Instagram",
        "whatsapp_link": "WhatsApp",
        "instagram_url": "URL do Instagram",
        "rating": "Avaliação",
        "review_count": "Avaliações",
        "score": "Score",
        "site_status": "Status do site",
        "observations": "Observações",
    }
    for key, label in labels.items():
        if lead.get(key) not in (None, "", []):
            lines.append(f"- **{label}:** {_texto_limitado(lead[key])}")
    lines.extend(["", "## Conversion pack", ""])
    pack = clean["conversion_pack"]
    lines.append(f"- **Status:** {pack.get('status', 'ausente')}")
    if pack.get("version"):
        lines.append(f"- **Versão:** {pack['version']}")
    if pack.get("strategy"):
        lines.extend(["", "### Estratégia", ""])
        if isinstance(pack["strategy"], Mapping):
            for key, value in pack["strategy"].items():
                if isinstance(value, list):
                    value = ", ".join(value)
                lines.append(f"- **{key}:** {value}")
        else:
            lines.append(str(pack["strategy"]))
    if pack.get("initial_message"):
        lines.extend(["", "### Mensagem inicial", "", f"> {pack['initial_message']}"])
    if pack.get("followups"):
        lines.extend(["", "### Follow-ups", ""])
        for followup in pack["followups"]:
            lines.append(f"- **{followup.get('objective', 'Follow-up')}:** {followup.get('message', '')}")
    lines.extend(["", "## Landing Page", ""])
    page = clean["landing_page"]
    if page:
        for key, value in page.items():
            lines.append(f"- **{key}:** {value}")
    else:
        lines.append("- Nenhuma Landing Page encontrada no contexto exportado.")
    lines.extend(["", "## Gate de investimento", ""])
    investment = clean["investment"]
    lines.append(f"- **Elegível:** {'sim' if investment['eligible'] else 'não'}")
    if investment.get("level"):
        lines.append(f"- **Nível:** {investment['level']}")
    for blocker in investment.get("blockers", []):
        lines.append(f"- **Blocker:** `{blocker}`")
    lines.extend(["", "## Handoff", ""])
    handoff = clean["handoff"]
    lines.append("- **ProspectOS possui:** " + ", ".join(handoff.get("prospectos_owns", [])))
    lines.append("- **Sol Advisor possui:** " + ", ".join(handoff.get("sol_advisor_owns", [])))
    lines.extend(["", "<!-- " + MANAGED_MARKER + " -->", ""])
    content = "\n".join(lines)
    if write:
        target_dir.mkdir(parents=True, exist_ok=True)
    item = _write_managed(target_dir / f"{slug}.md", content, write=write, force=force)
    return {
        "vault": str(vault),
        "lead_id": clean["lead_id"],
        "path": str(target_dir / f"{slug}.md"),
        "status": item.status,
        "reason": item.reason,
    }


def _vault_from_args(value: Optional[str]) -> Path:
    candidate = value or os.environ.get("PROSPECTOS_OBSIDIAN_VAULT")
    if not candidate:
        raise ObsidianSyncError("Informe --vault ou defina PROSPECTOS_OBSIDIAN_VAULT.")
    return Path(candidate)


def _load_json(path: Path) -> Mapping[str, Any]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObsidianSyncError(f"Não foi possível ler o JSON de contexto: {path}") from exc
    if not isinstance(parsed, Mapping):
        raise ObsidianSyncError("O contexto JSON precisa ser um objeto.")
    return parsed


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--vault", help="caminho absoluto do vault Obsidian")
    common.add_argument("--write", action="store_true", help="efetiva a escrita; sem isso apenas planeja")
    common.add_argument("--force", action="store_true", help="atualiza arquivos existentes não gerenciados")
    common.add_argument("--updated", help="timestamp ISO para reprodução/testes")

    project = sub.add_parser("init-project", parents=[common], help="cria as notas do projeto ProspectOS")
    project.add_argument("--repo", help="raiz do repositório; padrão: raiz deste checkout")

    lead = sub.add_parser("export-lead", parents=[common], help="exporta um contexto site-opportunity/v1")
    lead.add_argument("--context-json", required=True, help="JSON produzido pelo MCP ou por um harness local")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = _build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        vault = _vault_from_args(args.vault)
        if args.command == "init-project":
            result = export_project(
                vault,
                Path(args.repo).resolve() if args.repo else None,
                write=args.write,
                force=args.force,
                updated=args.updated,
            )
        else:
            result = export_lead(
                vault,
                _load_json(Path(args.context_json).resolve()),
                write=args.write,
                force=args.force,
                updated=args.updated,
            )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except ObsidianSyncError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
