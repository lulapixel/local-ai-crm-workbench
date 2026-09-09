import { useEffect } from "react"
import { useParams, useSearchParams, Link } from "react-router-dom"
import { useQuery } from "@tanstack/react-query"
import { Eye, ArrowLeft, AlertCircle, Loader2 } from "lucide-react"
import { landingPagesService } from "@/services/landingPagesService"
import { getTemplateRenderer } from "@/features/landing-pages/templates/registry"

export function LandingPageDemoPage() {
  const { slug } = useParams<{ slug: string }>()
  const [searchParams] = useSearchParams()
  const isPreview = searchParams.get("preview") === "1"

  useEffect(() => {
    // Adiciona meta noindex para não indexar páginas de preview em motores de busca
    let metaRobots = document.querySelector<HTMLMetaElement>("meta[name='robots']")
    if (!metaRobots) {
      metaRobots = document.createElement("meta")
      metaRobots.name = "robots"
      document.head.appendChild(metaRobots)
    }
    metaRobots.content = isPreview ? "noindex, nofollow" : "index, follow"

    return () => {
      if (metaRobots && isPreview) {
        metaRobots.content = "index, follow"
      }
    }
  }, [isPreview])

  const { data: landingPage, isLoading, isError } = useQuery({
    queryKey: ["landing-page-slug", slug, isPreview],
    queryFn: async () => {
      if (!slug) throw new Error("Slug não informado")
      if (isPreview) {
        return landingPagesService.obterPorSlug(slug)
      }
      return landingPagesService.obterPublicaPorSlug(slug)
    },
    enabled: Boolean(slug),
    retry: false,
  })

  if (isLoading) {
    return (
      <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="size-8 animate-spin text-primary" />
          <p>Carregando apresentação...</p>
        </div>
      </div>
    )
  }

  if (isError || !landingPage) {
    return (
      <div className="grid min-h-screen place-items-center bg-background p-6 text-center text-foreground">
        <div className="max-w-md space-y-4 rounded-xl border border-border bg-card p-6 shadow-sm">
          <AlertCircle className="mx-auto size-10 text-muted-foreground" />
          <h2 className="text-xl font-bold">Apresentação Indisponível</h2>
          <p className="text-sm text-muted-foreground">
            A demonstração solicitada não foi encontrada, está em rascunho ou não está publicada.
          </p>
          <Link
            to="/leads"
            className="inline-flex items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            <ArrowLeft className="size-4" />
            Voltar para os Leads
          </Link>
        </div>
      </div>
    )
  }

  const TemplateComponent = getTemplateRenderer(landingPage.template_key)

  return (
    <div className="min-h-screen bg-background">
      {isPreview && (
        <div className="sticky top-0 z-50 flex items-center justify-between border-b border-amber-500/30 bg-amber-950/90 px-4 py-2.5 text-xs text-amber-200 backdrop-blur">
          <div className="flex items-center gap-2">
            <Eye className="size-4 text-amber-400" />
            <span className="font-semibold">Modo Prévia Interna</span>
            <span className="hidden sm:inline">
              · Rascunho não publicado. Analytics desativado.
            </span>
          </div>
          <Link
            to="/leads"
            className="inline-flex items-center gap-1 text-amber-300 hover:text-amber-100 hover:underline"
          >
            <ArrowLeft className="size-3" />
            Voltar ao CRM
          </Link>
        </div>
      )}

      <TemplateComponent site={landingPage.spec} slug={landingPage.slug} isPreview={isPreview} />
    </div>
  )
}
