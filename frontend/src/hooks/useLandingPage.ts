import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import {
  landingPagesService,
  type GerarLandingPageOptions,
} from "@/services/landingPagesService"
import { ApiError } from "@/services/httpClient"

export function useLandingPage(placeId: string) {
  const queryClient = useQueryClient()
  const queryKey = ["landing-page", placeId]

  const query = useQuery({
    queryKey,
    queryFn: async () => {
      try {
        return await landingPagesService.obterPorLead(placeId)
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          return null
        }
        throw err
      }
    },
    enabled: Boolean(placeId),
    retry: false,
  })

  const gerarMutation = useMutation({
    mutationFn: (options?: GerarLandingPageOptions) =>
      landingPagesService.gerarParaLead(placeId, options),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      toast.success("Apresentação comercial gerada com sucesso!")
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao gerar apresentação comercial.")
    },
  })

  const publicarMutation = useMutation({
    mutationFn: (id: number) => landingPagesService.publicar(id),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      toast.success("Apresentação comercial publicada!")
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao publicar apresentação.")
    },
  })

  const despublicarMutation = useMutation({
    mutationFn: (id: number) => landingPagesService.despublicar(id),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      toast.success("Apresentação despublicada (retornou para rascunho).")
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao despublicar apresentação.")
    },
  })

  const arquivarMutation = useMutation({
    mutationFn: (id: number) => landingPagesService.arquivar(id),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      toast.info("Apresentação arquivada.")
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao arquivar apresentação.")
    },
  })

  const regenerarMutation = useMutation({
    mutationFn: ({ id, sections }: { id: number; sections?: string[] }) =>
      landingPagesService.regenerar(id, { sections }),
    onSuccess: (data) => {

      queryClient.setQueryData(queryKey, data)
      toast.success("Conteúdo regenerado com sucesso!")
    },
    onError: (err: Error) => {
      toast.error(err.message || "Erro ao regenerar conteúdo.")
    },
  })

  return {
    landingPage: query.data ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    gerar: gerarMutation,
    publicar: publicarMutation,
    despublicar: despublicarMutation,
    arquivar: arquivarMutation,
    regenerar: regenerarMutation,
  }
}
