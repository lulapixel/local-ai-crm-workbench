import { Clock, Eye, RotateCcw, Sparkles, User, History } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import type { LandingPageVersionSummary } from "@/services/landingPagesService"

interface VersionHistoryDrawerProps {
  isOpen: boolean
  onClose: () => void
  versions: LandingPageVersionSummary[]
  isLoading: boolean
  onPreviewVersion: (version: number) => void
  onRestoreVersion: (version: number) => void
  isRestoring: boolean
}

export function VersionHistoryDrawer({
  isOpen,
  onClose,
  versions,
  isLoading,
  onPreviewVersion,
  onRestoreVersion,
  isRestoring,
}: VersionHistoryDrawerProps) {
  if (!isOpen) return null

  const getBadgeForChangeType = (type: string, restoredFrom?: number | null) => {
    switch (type) {
      case "ai_regeneration":
        return (
          <Badge variant="outline" className="gap-1 border-purple-500/40 text-purple-300 bg-purple-500/10">
            <Sparkles className="size-3" />
            IA
          </Badge>
        )
      case "manual_edit":
        return (
          <Badge variant="outline" className="gap-1 border-blue-500/40 text-blue-300 bg-blue-500/10">
            <User className="size-3" />
            Edição Manual
          </Badge>
        )
      case "version_restore":
        return (
          <Badge variant="outline" className="gap-1 border-amber-500/40 text-amber-300 bg-amber-500/10">
            <RotateCcw className="size-3" />
            Restauração {restoredFrom ? `(v${restoredFrom})` : ""}
          </Badge>
        )
      case "initial_generation":
      default:
        return (
          <Badge variant="outline" className="text-muted-foreground">
            Geração Inicial
          </Badge>
        )
    }
  }

  const formatDate = (isoString: string) => {
    try {
      const d = new Date(isoString)
      return d.toLocaleString("pt-BR", {
        day: "2-digit",
        month: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
      })
    } catch {
      return isoString
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex justify-end bg-black/50 backdrop-blur-sm transition-opacity">
      <div className="flex flex-col w-full max-w-md bg-card border-l border-border h-full shadow-2xl animate-in slide-in-from-right duration-200">
        <div className="flex items-center justify-between p-4 border-b border-border bg-muted/30">
          <div className="flex items-center gap-2">
            <History className="size-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">
              Histórico de Versões ({versions.length})
            </h2>
          </div>
          <Button size="sm" variant="ghost" onClick={onClose}>
            Fechar
          </Button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3">
          {isLoading ? (
            <div className="text-center py-10 text-xs text-muted-foreground">
              Carregando histórico de versões...
            </div>
          ) : versions.length === 0 ? (
            <div className="text-center py-10 text-xs text-muted-foreground">
              Nenhuma versão encontrada no histórico.
            </div>
          ) : (
            versions.map((ver, idx) => {
              const isCurrent = idx === 0
              return (
                <div
                  key={ver.id || `v-${ver.version}`}
                  className={`rounded-lg border p-3.5 space-y-2.5 transition-all ${
                    isCurrent
                      ? "border-primary/40 bg-primary/5"
                      : "border-border bg-card hover:border-muted-foreground/30"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-foreground">
                        v{ver.version}
                      </span>
                      {getBadgeForChangeType(ver.change_type, ver.restored_from_version)}
                    </div>
                    {isCurrent && (
                      <Badge variant="default" className="text-[10px] py-0">
                        Atual
                      </Badge>
                    )}
                  </div>

                  <p className="text-xs text-foreground font-medium leading-snug">
                    {ver.description || `Versão ${ver.version}`}
                  </p>

                  <div className="flex items-center justify-between pt-1 border-t border-border/50 text-[11px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Clock className="size-3" />
                      {formatDate(ver.created_at)}
                    </span>

                    <div className="flex items-center gap-1.5">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 px-2 text-xs"
                        onClick={() => onPreviewVersion(ver.version)}
                      >
                        <Eye className="mr-1 size-3" />
                        Visualizar
                      </Button>

                      {!isCurrent && (
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 px-2 text-xs text-primary hover:bg-primary/10"
                          disabled={isRestoring}
                          onClick={() => onRestoreVersion(ver.version)}
                        >
                          <RotateCcw className="mr-1 size-3" />
                          Restaurar
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>
    </div>
  )
}
