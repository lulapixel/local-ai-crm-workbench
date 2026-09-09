import sqlite3
import csv

conn = sqlite3.connect('backend/leads.db')
c = conn.cursor()

c.execute("""
SELECT place_id, nome, categoria, endereco, num_avaliacoes, nota, telefone, site_url, instagram_url, query_origem
FROM leads
WHERE nome LIKE '%Nelson%' OR nome LIKE '%Like-Brazil%' OR nome LIKE '%Renovare%'
""")

rows = c.fetchall()
print("=== LEADS TABLE DETAILS ===")
for r in rows:
    print(f"Nome: {r[1]}")
    print(f"Categoria: {r[2]}")
    print(f"Endereço: {r[3]}")
    print(f"Notas/Avaliações: {r[5]} ({r[4]})")
    print(f"Telefone: {r[6]}")
    print(f"Site: {r[7]}")
    print(f"Instagram: {r[8]}")
    print(f"Query: {r[9]}")
    print("-" * 50)

print("\n=== RAW SCRAPED CSV DETAILS ===")
with open('backend/saidas/bruto_recife_moveis.csv', mode='r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        title = row.get('title', '')
        if 'Nelson' in title or 'Like' in title or 'Renovare' in title:
            print(f"Title: {title}")
            print(f"Category: {row.get('category')}")
            print(f"Address: {row.get('address')}")
            print(f"Phone: {row.get('phone')}")
            print(f"Website: {row.get('website')}")
            print("=" * 50)
