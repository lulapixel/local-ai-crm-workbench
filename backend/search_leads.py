import sqlite3

conn = sqlite3.connect('backend/leads.db')
cursor = conn.cursor()

query = """
SELECT place_id, nome, categoria, endereco, num_avaliacoes, nota, telefone, site_url, site_status
FROM leads
WHERE nome LIKE '%movel%' OR nome LIKE '%móvel%'
   OR nome LIKE '%marcenaria%' OR nome LIKE '%planejado%'
   OR categoria LIKE '%movel%' OR categoria LIKE '%marcenaria%'
"""
cursor.execute(query)
rows = cursor.fetchall()
print(f"Found {len(rows)} matching leads in DB:")
for r in rows:
    print(r)
