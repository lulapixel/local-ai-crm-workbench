import { useState, useCallback } from "react"
import { useQuery, useQueryClient } from "@tanstack/react-query"
import { landingPagesService, type LandingPageResponse } from "@/services/landingPagesService"

import { toast } from "sonner"

export function useLandingPageHistory(
  lpId: number,
  onVersionRestored?: (updatedLp: LandingPageResponse) => void
) {
  const queryClient = useQueryClient()
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [previewVersionNumber, setPreviewVersionNumber] = useState<number | null>(null)
  const [isRestoring, setIsRestoring] = useState(false)

  // Query de lista de histórico
  const historyQuery = useQuery({
    queryKey: ["landing-page-history", lpId],
    queryFn: () => landingPagesService.obterHistorico(lpId),
    enabled: Boolean(lpId && isDrawerOpen),
  })

  // Query para buscar detalhe da versão em visualização
  const versionDetailQuery = useQuery({
    queryKey: ["landing-page-version-detail", lpId, previewVersionNumber],
    queryFn: () => landingPagesService.obterVersaoHistorico(lpId, previewVersionNumber!),
    enabled: Boolean(lpId && previewVersionNumber !== null),
  })

  // Recarregar lista do histórico
  const refetchHistory = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ["landing-page-history", lpId] })
  }, [queryClient, lpId])

  // Restaurar versão
  const restoreVersion = useCallback(
    async (version: number): Promise<boolean> => {
      const confirmText = `Restaurar a versão ${version}? A versão atual será preservada no histórico e uma nova versão será criada.`
      if (!window.confirm(confirmText)) {
        return false
      }

      setIsRestoring(true)
      try {
        const updated = await landingPagesService.restaurarVersao(lpId, version)
        toast.success(`Versão ${version} restaurada com sucesso!`)
        refetchHistory()
        setPreviewVersionNumber(null)
        if (onVersionRestored) {
          onVersionRestored(updated)
        }
        return true
      } catch (err) {
        console.error("Erro ao restaurar versão:", err)
        toast.error("Falha ao restaurar versão do histórico.")
        return false
      } finally {
        setIsRestoring(false)
      }
    },
    [lpId, refetchHistory, onVersionRestored]
  )

  return {
    isDrawerOpen,
    setIsDrawerOpen,
    versions: historyQuery.data?.versions || [],
    isLoadingHistory: historyQuery.isLoading,
    previewVersionNumber,
    setPreviewVersionNumber,
    previewVersionDetail: versionDetailQuery.data || null,
    isLoadingVersionDetail: versionDetailQuery.isLoading,
    isRestoring,
    restoreVersion,
    refetchHistory,
  }
}
