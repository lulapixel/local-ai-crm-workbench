"""Constantes de domínio compartilhadas entre os módulos de rotas e jobs."""

STATUS_VALIDOS = {"novo", "contatado", "respondeu", "fechou", "recusou", "ignorado"}
STATUS_QUE_ENCERRAM_FOLLOWUP = {"fechou", "recusou", "ignorado"}

# Ordem "natural" do funil de prospecção - da entrada até o fechamento.
# "recusou" fica de fora do funil (é uma saída, não um estágio de progresso).
ESTAGIOS_FUNIL = ["novo", "contatado", "respondeu", "fechou"]

PRIORIDADES_VALIDAS = {"alta", "media", "baixa", "descartado"}

MAX_CARACTERES_OBSERVACOES = 5000
MAX_CARACTERES_TAGS = 500
MAX_LINHAS_QUERIES_BUSCA = 50
MAX_CARACTERES_POR_LINHA_QUERY = 200
MAX_CARACTERES_SUGESTAO_DM = 2000
MAX_CARACTERES_JUSTIFICATIVA = 1000
MAX_CARACTERES_NICHO_INSTAGRAM = 100
MAX_CARACTERES_NICHO_ALVO = 100
MAX_CARACTERES_OBSERVACOES_INSTAGRAM = 5000
MAX_CARACTERES_TAGS_INSTAGRAM = 500
MAX_CARACTERES_TITULO_TEMPLATE = 100
MAX_CARACTERES_TEXTO_TEMPLATE = 3000

DIAS_PARA_LEAD_DIFICIL = 5

# Limite de ids por ação em lote. Protege contra o limite de variáveis vinculadas
# do SQLite (~999) num IN (...) e contra payloads absurdos.
MAX_IDS_BULK = 500

# Busca por mapa (pino + raio)
MAX_AREAS_BUSCA_MAPA = 5
MAX_NICHOS_BUSCA_MAPA = 15
MAX_CARACTERES_NICHO_BUSCA = 100
MAX_CARACTERES_ROTULO_AREA = 120
RAIO_MIN_METROS = 500
RAIO_MAX_METROS = 50_000
