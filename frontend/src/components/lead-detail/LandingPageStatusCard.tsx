import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import {
  Check,
  Copy,
  Edit,
  ExternalLink,
  Eye,
  Globe,
  Loader2,
  RefreshCw,
  Sparkles,
  Archive,
  AlertCircle,
  TrendingUp,
  MessageCircle,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useLandingPage } from "@/hooks/useLandingPage"
import { landingPagesService } from "@/services/landingPagesService"
import { PublicationChecklistDialog } from "@/features/landing-pages/editor/components/PublicationChecklistDialog"
import { toast } from "sonner"
import type { Lead } from "@/types/lead"
import { safeExternalUrl } from "@/lib/safeExternalUrl"

interface LandingPageStatusCardProps {
  lead: Lead
}

export function LandingPageStatusCard({ lead }: LandingPageStatusCardProps) {
  const navigate = useNavigate()
  const {
    landingPage,
    isLoading,
    isError,
    gerar,
    publicar,
    despublicar,
    arquivar,
  } = useLandingPage(lead.place_id)

  const [copiado, setCopiado] = useState(false)
  const [isChecklistOpen, setIsChecklistOpen] = useState(false)

  const { data: analytics } = useQuery({
    queryKey: ["lp-analytics", landingPage?.id],
    queryFn: () => landingPagesService.obterAnalytics(landingPage!.id),
    enabled: Boolean(landingPage?.id && landingPage?.status === "published"),
    retry: false,
  })

  const handleCopiarLink = () => {
    if (!landingPage) return
    const path = landingPage.public_url || landingPage.preview_url
    const safePath = safeExternalUrl(path, { allowRelative: true })
    if (!safePath) {
      toast.error("O link da apresentação não é válido.")
      return
    }
    const fullUrl = safePath.startsWith("/")
      ? `${window.location.origin}${safePath}`
      : safePath
    navigator.clipboard.writeText(fullUrl)
    setCopiado(true)
    toast.success("Link da apresentação copiado para a área de transferência!")
    setTimeout(() => setCopiado(false), 2000)
  }

  const isGerando = gerar.isPending || isLoading

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary" />
          <h4 className="text-sm font-semibold text-foreground">
            Apresentação Comercial
          </h4>
        </div>
        {landingPage && !isGerando && (
          <Badge
            variant={
              landingPage.status === "published"
                ? "default"
                : landingPage.status === "archived"
                ? "outline"
                : "secondary"
            }
            className="text-xs capitalize"
          >
            {landingPage.status === "published"
              ? "Publicada"
              : landingPage.status === "archived"
              ? "Arquivada"
              : "Rascunho"}
          </Badge>
        )}
      </div>

      {isGerando ? (
        <div className="flex items-center gap-2.5 rounded-md bg-muted/50 p-3 text-xs text-muted-foreground">
          <Loader2 className="size-4 animate-spin text-primary" />
          <span>Criando estrutura e conteúdo com IA...</span>
        </div>
      ) : isError ? (
        <div className="space-y-2">
          <p className="text-xs text-destructive">
            Não foi possível carregar a apresentação deste lead.
          </p>
          <Button
            size="sm"
            variant="outline"
            onClick={() => gerar.mutate({ forceRegenerate: true })}
          >
            <RefreshCw className="mr-1.5 size-3.5" />
            Tentar novamente
          </Button>
        </div>
      ) : !landingPage ? (
        <div className="space-y-2">
          <p className="text-xs text-muted-foreground">
            Nenhuma apresentação gerada para este lead ainda.
          </p>
          <Button
            size="sm"
            className="w-full"
            onClick={() => gerar.mutate({ forceRegenerate: false })}
          >
            <Sparkles className="mr-1.5 size-3.5" />
            Gerar apresentação
          </Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="rounded-md bg-muted/40 p-2.5 text-xs text-muted-foreground space-y-1">
            <p className="font-medium text-foreground">
              {landingPage?.spec?.brand?.name || lead?.nome || "Apresentação"}
            </p>
            <p className="truncate">
              Slug: <code className="text-primary font-mono">{landingPage.slug}</code>
            </p>
          </div>

          {landingPage.publication_configured === false && (
            <div className="flex items-center gap-2 rounded-md bg-amber-500/10 border border-amber-500/20 p-2 text-xs text-amber-300">
              <AlertCircle className="size-3.5 text-amber-400 shrink-0" />
              <span>Publicação externa não configurada (servindo em preview interno).</span>
            </div>
          )}

          {/* Seção de Métricas de Analytics */}
          {analytics && landingPage.status === "published" && (
            <div className="rounded-md border border-border bg-muted/20 p-3 space-y-2 text-xs text-muted-foreground">
              <div className="flex items-center justify-between font-medium text-foreground">
                <span className="flex items-center gap-1.5">
                  <TrendingUp className="size-3.5 text-primary" />
                  Analytics de Acesso
                </span>
                {analytics.last_view_at && (
                  <span className="text-[0.7rem] text-muted-foreground">
                    {new Date(analytics.last_view_at).toLocaleDateString("pt-BR", {
                      day: "2-digit",
                      month: "2-digit",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                )}
              </div>

              <div className="grid grid-cols-2 gap-2 text-[0.75rem]">
                <div className="bg-background/50 rounded p-1.5 border border-border/40">
                  <span className="text-muted-foreground block text-[0.68rem]">Visualizações</span>
                  <strong className="text-foreground text-sm font-semibold">{analytics.page_views}</strong>
                </div>
                <div className="bg-background/50 rounded p-1.5 border border-border/40">
                  <span className="text-muted-foreground block text-[0.68rem]">Visitantes est.</span>
                  <strong className="text-foreground text-sm font-semibold">{analytics.estimated_sessions}</strong>
                </div>
                <div className="bg-background/50 rounded p-1.5 border border-border/40">
                  <span className="text-muted-foreground block text-[0.68rem]">Cliques WhatsApp</span>
                  <strong className="text-foreground text-sm font-semibold">{analytics.whatsapp_clicks}</strong>
                </div>
                <div className="bg-background/50 rounded p-1.5 border border-border/40">
                  <span className="text-muted-foreground block text-[0.68rem]">Simulações conc.</span>
                  <strong className="text-foreground text-sm font-semibold">{analytics.simulator_completions}</strong>
                </div>
              </div>

              {/* Sinais comerciais */}
              {analytics.last_view_at && (
                <div className="flex items-center gap-1.5 rounded bg-emerald-500/10 p-1.5 text-[0.7rem] font-medium text-emerald-400 border border-emerald-500/20">
                  <Sparkles className="size-3 shrink-0 text-emerald-400" />
                  <span>Este lead visualizou a apresentação recentemente.</span>
                </div>
              )}

              {analytics.whatsapp_clicks > 0 && (
                <div className="flex items-center gap-1.5 rounded bg-emerald-500/10 p-1.5 text-[0.7rem] font-medium text-emerald-400 border border-emerald-500/20">
                  <MessageCircle className="size-3 shrink-0 text-emerald-400" />
                  <span>Houve clique no WhatsApp após visualizar a página.</span>
                </div>
              )}
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            {/* Visualizar Preview */}
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                const url = safeExternalUrl(landingPage.preview_url, { allowRelative: true })
                if (url) window.open(url, "_blank", "noopener,noreferrer")
                else toast.error("A prévia não tem um link válido.")
              }}
              title="Abrir prévia interna com selo de rascunho"
            >
              <Eye className="mr-1.5 size-3.5" />
              Visualizar
            </Button>

            {/* Editar Landing Page */}
            {(landingPage.status === "draft" || landingPage.status === "published") && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => navigate(`/landing-pages/${landingPage.id}/edit`)}
                title="Abrir editor visual da landing page"
              >
                <Edit className="mr-1.5 size-3.5" />
                Editar
              </Button>
            )}

            {/* Ações por status */}
            {landingPage.status === "draft" && (
              <>
                <Button
                  size="sm"
                  variant="default"
                  onClick={() => setIsChecklistOpen(true)}
                  disabled={publicar.isPending}
                >
                  {publicar.isPending ? (
                    <Loader2 className="mr-1.5 size-3.5 animate-spin" />
                  ) : (
                    <Globe className="mr-1.5 size-3.5" />
                  )}
                  Publicar
                </Button>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => arquivar.mutate(landingPage.id)}
                  disabled={arquivar.isPending}
                  title="Arquivar apresentação"
                >
                  <Archive className="size-3.5 text-muted-foreground" />
                </Button>
              </>
            )}

            {landingPage.status === "published" && (
              <>
                <Button size="sm" variant="default" onClick={handleCopiarLink}>
                  {copiado ? (
                    <Check className="mr-1.5 size-3.5 text-emerald-400" />
                  ) : (
                    <Copy className="mr-1.5 size-3.5" />
                  )}
                  {copiado ? "Copiado!" : "Copiar link"}
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    const url = safeExternalUrl(
                      landingPage.public_url || landingPage.preview_url,
                      { allowRelative: true },
                    )
                    if (url) window.open(url, "_blank", "noopener,noreferrer")
                    else toast.error("A apresentação não tem um link válido.")
                  }}
                >
                  <ExternalLink className="mr-1.5 size-3.5" />
                  Abrir
                </Button>

                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setIsChecklistOpen(true)}
                  disabled={publicar.isPending}
                  title="Republicar versão atualizada da página"
                >
                  <RefreshCw className="mr-1.5 size-3.5" />
                  Republicar
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => despublicar.mutate(landingPage.id)}
                  disabled={despublicar.isPending}
                  className="text-xs text-muted-foreground hover:text-foreground"
                >
                  Despublicar
                </Button>
              </>
            )}

            {landingPage.status === "archived" && (
              <Button
                size="sm"
                variant="outline"
                onClick={() => gerar.mutate({ forceRegenerate: true })}
                disabled={gerar.isPending}
              >
                <RefreshCw className="mr-1.5 size-3.5" />
                Regerar apresentação
              </Button>
            )}
          </div>
        </div>
      )}

      {landingPage && (
        <PublicationChecklistDialog
          open={isChecklistOpen}
          onOpenChange={setIsChecklistOpen}
          isPublishing={publicar.isPending}
          publicationConfigured={landingPage.publication_configured !== false}
          onConfirmPublish={() => publicar.mutate(landingPage.id)}
        />
      )}
    </div>
  )
}
