import { ArrowLeft, RotateCcw, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import type { LandingPageVersionDetail } from "@/services/landingPagesService"
import { LandingPageTemplate } from "@/features/landing-pages/LandingPageTemplate"

interface VersionPreviewDialogProps {
  isOpen: boolean
  onClose: () => void
  versionDetail: LandingPageVersionDetail | null
  isLoading: boolean
  onRestoreVersion: (version: number) => void
  isRestoring: boolean
}

export function VersionPreviewDialog({
  isOpen,
  onClose,
  versionDetail,
  isLoading,
  onRestoreVersion,
  isRestoring,
}: VersionPreviewDialogProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background">
      {/* Top Banner Notice */}
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-amber-500/30 bg-amber-500/10 px-4 py-2.5 text-xs text-amber-200">
        <div className="flex items-center gap-2">
          <Button size="sm" variant="ghost" className="h-7 px-2" onClick={onClose}>
            <ArrowLeft className="mr-1 size-3.5" />
            Voltar à versão atual
          </Button>
          <span className="font-semibold">
            Visualizando versão {versionDetail?.version || "..."} — esta não é a versão atual
          </span>
        </div>

        {versionDetail && (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="default"
              disabled={isRestoring}
              onClick={() => onRestoreVersion(versionDetail.version)}
            >
              {isRestoring ? (
                <Loader2 className="mr-1.5 size-3.5 animate-spin" />
              ) : (
                <RotateCcw className="mr-1.5 size-3.5" />
              )}
              Restaurar esta versão
            </Button>
          </div>
        )}
      </header>

      {/* Main Content / Template */}
      <div className="flex-1 overflow-y-auto bg-neutral-950">
        {isLoading || !versionDetail ? (
          <div className="grid min-h-full place-items-center text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <Loader2 className="size-5 animate-spin text-primary" />
              <span>Carregando versão {versionDetail?.version || ""}...</span>
            </div>
          </div>
        ) : (
          <div className="mx-auto min-h-full max-w-7xl">
            <LandingPageTemplate site={versionDetail.spec} />
          </div>
        )}
      </div>
    </div>
  )
}
