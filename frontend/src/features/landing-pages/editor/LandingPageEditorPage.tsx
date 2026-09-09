import { useParams, useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { useCallback } from "react"

import { landingPagesService, type LandingPageResponse } from "@/services/landingPagesService"
import { useLandingPageEditor } from "./hooks/useLandingPageEditor"
import { useUnsavedChanges } from "./hooks/useUnsavedChanges"
import { useLandingPageHistory } from "./hooks/useLandingPageHistory"
import { LandingPageEditorShell } from "./LandingPageEditorShell"
import { Loader2, AlertTriangle, ArrowLeft } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { AiTone } from "./components/AiRegenerationDialog"
import { toast } from "sonner"

export function LandingPageEditorPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const lpId = Number(id)

  const {
    data: initialData,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["landing-page-editor", lpId],
    queryFn: () => landingPagesService.obterPorId(lpId),
    enabled: Boolean(lpId && !isNaN(lpId)),
    staleTime: 0,
  })

  if (isLoading || !initialData) {
    return (
      <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="size-8 animate-spin text-primary" />
          <p>Carregando editor visual da Landing Page...</p>
        </div>
      </div>
    )
  }

  if (isError || !initialData) {
    return (
      <div className="grid min-h-screen place-items-center bg-background p-4 text-center">
        <div className="max-w-md space-y-4 rounded-xl border border-border bg-card p-6 shadow-sm">
          <AlertTriangle className="mx-auto size-10 text-destructive" />
          <h2 className="text-lg font-semibold text-foreground">
            Não foi possível carregar a Landing Page
          </h2>
          <p className="text-sm text-muted-foreground">
            {error instanceof Error ? error.message : "A Landing Page solicitada não foi encontrada."}
          </p>
          <Button onClick={() => navigate(-1)} variant="outline">
            <ArrowLeft className="mr-2 size-4" />
            Voltar
          </Button>
        </div>
      </div>
    )
  }

  return <LandingPageEditorPageContent initialData={initialData} />
}

function LandingPageEditorPageContent({
  initialData,
}: {
  initialData: LandingPageResponse
}) {
  const editor = useLandingPageEditor(initialData)

  // Callback chamado após restauração de versão
  const handleVersionRestored = useCallback(
    (updatedLp: LandingPageResponse) => {
      editor.updateDraft(() => updatedLp.spec)
      // Forçar atualização do editor sem reload
      window.location.reload()
    },
    [editor]
  )

  const history = useLandingPageHistory(editor.lpResponse.id, handleVersionRestored)

  // Interceptador de alterações não salvas
  useUnsavedChanges(editor.isDirty)

  // Regeneração parcial por seção via IA
  const handleRegenerateSection = useCallback(
    async (sections: string[], tone: AiTone, instruction: string): Promise<boolean> => {
      if (editor.isDirty) {
        toast.error("Salve ou descarte suas alterações antes de usar a IA.")
        return false
      }

      try {
        const updated = await landingPagesService.regenerar(editor.lpResponse.id, {
          sections,
          tone,
          instruction,
        })
        toast.success(`Seção ${sections.join(", ")} reescrita pela IA com sucesso!`)
        editor.updateDraft(() => updated.spec)
        history.refetchHistory()
        return true
      } catch (err) {
        console.error("Erro ao regenerar seção via IA:", err)
        toast.error("Falha ao reescrever seção via IA. O conteúdo atual foi preservado.")
        return false
      }
    },
    [editor, history]
  )

  return (
    <LandingPageEditorShell
      lpResponse={editor.lpResponse}
      draftSpec={editor.draftSpec}
      saveStatus={editor.saveStatus}
      isDirty={editor.isDirty}
      isSaving={editor.isSaving}
      validationErrors={editor.validationErrors}
      onSave={editor.saveChanges}
      onDiscard={editor.discardChanges}
      updateContentField={editor.updateContentField}
      updateContactField={editor.updateContactField}
      updateSeoField={editor.updateSeoField}
      updatePaletteColor={editor.updatePaletteColor}
      updateDraft={editor.updateDraft}
      updateService={editor.updateService}
      addService={editor.addService}
      removeService={editor.removeService}
      moveService={editor.moveService}
      updateTrustItem={editor.updateTrustItem}
      addTrustItem={editor.addTrustItem}
      removeTrustItem={editor.removeTrustItem}
      updateTestimonial={editor.updateTestimonial}
      addTestimonial={editor.addTestimonial}
      removeTestimonial={editor.removeTestimonial}
      updateFaq={editor.updateFaq}
      addFaq={editor.addFaq}
      removeFaq={editor.removeFaq}
      historyVersions={history.versions}
      isLoadingHistory={history.isLoadingHistory}
      onRegenerateSection={handleRegenerateSection}
      onPreviewVersion={(v) => history.setPreviewVersionNumber(v)}
      onRestoreVersion={(v) => history.restoreVersion(v)}
      previewVersionDetail={history.previewVersionDetail}
      isLoadingVersionDetail={history.isLoadingVersionDetail}
      previewVersionNumber={history.previewVersionNumber}
      onClosePreviewVersion={() => history.setPreviewVersionNumber(null)}
      isRestoring={history.isRestoring}
    />
  )
}
