import sqlite3
import json

conn = sqlite3.connect('backend/leads.db')
cursor = conn.cursor()

query = """
SELECT place_id, nome, categoria, endereco, nota, num_avaliacoes, telefone, whatsapp_link, site_url, site_status, instagram_url, mensagem_gerada
FROM leads
WHERE (nome LIKE '%movel%' OR nome LIKE '%móvel%' OR nome LIKE '%marcenaria%' OR nome LIKE '%planejado%' OR categoria LIKE '%movel%' OR categoria LIKE '%marcenaria%' OR query_origem LIKE '%moveis%')
  AND num_avaliacoes >= 10
ORDER BY num_avaliacoes DESC, nota DESC
"""

cursor.execute(query)
rows = cursor.fetchall()

print(f"Total qualified candidates found: {len(rows)}\n")

candidates = []
for r in rows:
    place_id, nome, categoria, endereco, nota, num_avaliacoes, telefone, whatsapp_link, site_url, site_status, instagram_url, mensagem_gerada = r

    # Filter for no site or bad site
    has_site = bool(site_url and site_url.strip() and not site_url.startswith("https://instagram.com") and not site_url.startswith("https://facebook.com"))

    candidates.append({
        "nome": nome,
        "categoria": categoria,
        "endereco": endereco,
        "nota": nota,
        "num_avaliacoes": num_avaliacoes,
        "telefone": telefone,
        "whatsapp_link": whatsapp_link,
        "site_url": site_url if has_site else None,
        "site_status": site_status,
        "instagram_url": instagram_url,
        "tem_site": has_site
    })

# Sort by preference: Sem site or Site Fraco, high reviews, high rating
no_site_candidates = [c for c in candidates if not c["tem_site"]]
with_site_candidates = [c for c in candidates if c["tem_site"]]

print("--- TOP LEADS SEM SITE (QUALIFICADOS) ---")
for idx, c in enumerate(no_site_candidates[:5], 1):
    print(f"{idx}. {c['nome']}")
    print(f"   Nota: {c['nota']} ({c['num_avaliacoes']} avaliações)")
    print(f"   Endereço: {c['endereco']}")
    print(f"   Telefone/WhatsApp: {c['telefone']} | Link WA: {c['whatsapp_link']}")
    print(f"   Site: Sem site (Apenas Google/Maps)")
    print()

if len(no_site_candidates) < 3:
    print("--- TOP LEADS COM SITE FRACO / INSTAGRAM ---")
    for idx, c in enumerate(with_site_candidates[:5], 1):
        print(f"{idx}. {c['nome']}")
        print(f"   Nota: {c['nota']} ({c['num_avaliacoes']} avaliações)")
        print(f"   Site: {c['site_url']} ({c['site_status']})")
        print(f"   Telefone: {c['telefone']}")
        print()
