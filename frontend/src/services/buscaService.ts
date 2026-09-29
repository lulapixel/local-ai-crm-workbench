import { httpClient } from "@/services/httpClient"
import type { AreaBuscaPayload, BuscaHistorico, EstadoBusca } from "@/types/busca"

export const buscaService = {
  disparar: (queries: string, apenasNovos: boolean) =>
    httpClient.post<{ ok: true }>("/api/buscar", { queries, apenas_novos: apenasNovos }),

  dispararPorMapa: (nichos: string[], areas: AreaBuscaPayload[], apenasNovos: boolean) =>
    httpClient.post<{ ok: true }>("/api/buscar", { nichos, areas, apenas_novos: apenasNovos }),

  consultarStatus: () => httpClient.get<EstadoBusca>("/api/buscar/status"),

  historico: () =>
    httpClient.get<{ buscas: BuscaHistorico[] }>("/api/buscar/historico"),
}
