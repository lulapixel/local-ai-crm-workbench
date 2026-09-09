import { useNavigate } from "react-router-dom"
import { ArrowLeft, ExternalLink, Save, RotateCcw, Loader2, History } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { SaveStatus } from "./editor-types"
import type { LandingPageResponse } from "@/services/landingPagesService"

interface LandingPageEditorHeaderProps {
  lpResponse: LandingPageResponse
  saveStatus: SaveStatus
  isDirty: boolean
  isSaving: boolean
  onSave: () => void
  onDiscard: () => void
  onToggleMobilePreview?: () => void
  isMobilePreviewOpen?: boolean
  onOpenHistory?: () => void
}

export function LandingPageEditorHeader({
  lpResponse,
  saveStatus,
  isDirty,
  isSaving,
  onSave,
  onDiscard,
  onToggleMobilePreview,
  isMobilePreviewOpen,
  onOpenHistory,
}: LandingPageEditorHeaderProps) {

  const navigate = useNavigate()

  const getStatusBadge = () => {
    switch (saveStatus) {
      case "saving":
        return (
          <Badge variant="outline" className="gap-1 border-amber-500/50 text-amber-400 bg-amber-500/10">
            <Loader2 className="size-3 animate-spin" />
            Salvando...
          </Badge>
        )
      case "saved":
        return (
          <Badge variant="outline" className="border-emerald-500/50 text-emerald-400 bg-emerald-500/10">
            Salvo
          </Badge>
        )
      case "error":
        return (
          <Badge variant="destructive">
            Erro ao salvar
          </Badge>
        )
      case "dirty":
        return (
          <Badge variant="secondary" className="bg-amber-500/15 text-amber-300">
            Alterações não salvas
          </Badge>
        )
      case "clean":
      default:
        return (
          <Badge variant="outline" className="text-muted-foreground">
            Sem alterações
          </Badge>
        )
    }
  }

  return (
    <header className="sticky top-0 z-30 flex flex-wrap items-center justify-between gap-3 border-b border-border bg-background/95 px-4 py-3 backdrop-blur">
      <div className="flex items-center gap-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => {
            if (isDirty) {
              if (!window.confirm("Existem alterações não salvas. Deseja sair mesmo assim?")) {
                return
              }
            }
            navigate(-1)
          }}
          title="Voltar ao lead"
        >
          <ArrowLeft className="mr-1.5 size-4" />
          Voltar
        </Button>

        <div className="h-4 w-px bg-border hidden sm:block" />

        <div className="flex items-center gap-2">
          <h1 className="text-sm font-semibold text-foreground truncate max-w-[200px] sm:max-w-xs">
            {lpResponse?.spec?.brand?.name || "Editor de Landing Page"}
          </h1>
          {getStatusBadge()}
        </div>
      </div>

      <div className="flex items-center gap-2">
        {/* Toggle para mobile */}
        {onToggleMobilePreview && (
          <Button
            size="sm"
            variant="outline"
            className="lg:hidden"
            onClick={onToggleMobilePreview}
          >
            {isMobilePreviewOpen ? "Editar campos" : "Visualizar prévia"}
          </Button>
        )}

        {/* Histórico de Versões */}
        {onOpenHistory && (
          <Button
            size="sm"
            variant="outline"
            onClick={onOpenHistory}
            title="Abrir histórico de versões da Landing Page"
          >
            <History className="mr-1.5 size-3.5" />
            Histórico
          </Button>
        )}

        {/* Abrir apresentação pública em nova aba */}
        <Button
          size="sm"
          variant="outline"
          onClick={() => window.open(`/demos/${lpResponse.slug}`, "_blank", "noopener,noreferrer")}
          title="Visualizar apresentação pública"
        >

          <ExternalLink className="mr-1.5 size-3.5" />
          <span className="hidden sm:inline">Visualizar</span> apresentação
        </Button>

        {/* Descartar alterações */}
        <Button
          size="sm"
          variant="ghost"
          disabled={!isDirty || isSaving}
          onClick={onDiscard}
          className="text-muted-foreground hover:text-foreground"
        >
          <RotateCcw className="mr-1.5 size-3.5" />
          <span className="hidden sm:inline">Descartar</span>
        </Button>

        {/* Salvar */}
        <Button
          size="sm"
          disabled={!isDirty || isSaving}
          onClick={onSave}
          className="min-w-[90px]"
        >
          {isSaving ? (
            <Loader2 className="mr-1.5 size-3.5 animate-spin" />
          ) : (
            <Save className="mr-1.5 size-3.5" />
          )}
          Salvar
        </Button>
      </div>
    </header>
  )
}
