import { lazy, Suspense } from "react"
import { BrowserRouter, Route, Routes } from "react-router-dom"
import { QueryClientProvider } from "@tanstack/react-query"
import { TooltipProvider } from "@/components/ui/tooltip"
import { Toaster } from "@/components/ui/sonner"
import { queryClient } from "@/lib/queryClient"
import { PaletaComando } from "@/components/shared/PaletaComando"

const DashboardPage = lazy(() =>
  import("@/pages/DashboardPage").then((module) => ({
    default: module.DashboardPage,
  })),
)

const TarefasPage = lazy(() =>
  import("@/pages/TarefasPage").then((module) => ({
    default: module.TarefasPage,
  })),
)

const SessaoProspeccaoPage = lazy(() =>
  import("@/pages/SessaoProspeccaoPage").then((module) => ({
    default: module.SessaoProspeccaoPage,
  })),
)

const LeadsMapsPage = lazy(() =>
  import("@/pages/LeadsMapsPage").then((module) => ({
    default: module.LeadsMapsPage,
  })),
)

const AnalyticsPage = lazy(() =>
  import("@/pages/AnalyticsPage").then((module) => ({
    default: module.AnalyticsPage,
  })),
)

const InstagramPage = lazy(() =>
  import("@/pages/InstagramPage").then((module) => ({
    default: module.InstagramPage,
  })),
)

const InstagramAnalyticsPage = lazy(() =>
  import("@/pages/InstagramAnalyticsPage").then((module) => ({
    default: module.InstagramAnalyticsPage,
  })),
)

const InstagramArquivadosPage = lazy(() =>
  import("@/pages/InstagramArquivadosPage").then((module) => ({
    default: module.InstagramArquivadosPage,
  })),
)

const ConfiguracoesPage = lazy(() =>
  import("@/pages/ConfiguracoesPage").then((module) => ({
    default: module.ConfiguracoesPage,
  })),
)

const DocumentacaoPage = lazy(() =>
  import("@/pages/DocumentacaoPage").then((module) => ({
    default: module.DocumentacaoPage,
  })),
)

const EsteticaPremiumDemoPage = lazy(() =>
  import("@/pages/demos/EsteticaPremiumDemoPage").then((module) => ({
    default: module.EsteticaPremiumDemoPage,
  })),
)

const LandingPageDemoPage = lazy(() =>
  import("@/pages/demos/LandingPageDemoPage").then((module) => ({
    default: module.LandingPageDemoPage,
  })),
)

const LandingPageEditorPage = lazy(() =>
  import("@/features/landing-pages/editor/LandingPageEditorPage").then((module) => ({
    default: module.LandingPageEditorPage,
  })),
)

const OutreachReviewQueuePage = lazy(() =>
  import("@/features/outreach/review-queue/OutreachReviewQueuePage").then((module) => ({
    default: module.OutreachReviewQueuePage,
  })),
)

const DailyOutreachPage = lazy(() =>
  import("@/features/outreach/daily/DailyOutreachPage").then((module) => ({
    default: module.DailyOutreachPage,
  })),
)

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <BrowserRouter>
          <PaletaComando />
          <Suspense
            fallback={
              <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
                Carregando ProspectOS...
              </div>
            }
          >
            <Routes>
              <Route path="/" element={<DashboardPage />} />
            <Route
              path="/abordagens"
              element={
                <Suspense
                  fallback={
                    <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
                      Carregando Central de Abordagens...
                    </div>
                  }
                >
                  <OutreachReviewQueuePage />
                </Suspense>
              }
            />
            <Route
              path="/outreach/hoje"
              element={
                <Suspense
                  fallback={
                    <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
                      Carregando Prospecção do dia...
                    </div>
                  }
                >
                  <DailyOutreachPage />
                </Suspense>
              }
            />
            <Route path="/tarefas" element={<TarefasPage />} />
            <Route path="/sessao" element={<SessaoProspeccaoPage />} />
            <Route path="/leads" element={<LeadsMapsPage />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/instagram" element={<InstagramPage />} />
            <Route path="/instagram/analytics" element={<InstagramAnalyticsPage />} />
            <Route path="/instagram/arquivados" element={<InstagramArquivadosPage />} />
            <Route path="/configuracoes" element={<ConfiguracoesPage />} />
            <Route path="/documentacao" element={<DocumentacaoPage />} />
            <Route
              path="/demos/estetica-premium"
              element={
                <Suspense
                  fallback={
                    <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
                      Carregando demonstração...
                    </div>
                  }
                >
                  <EsteticaPremiumDemoPage />
                </Suspense>
              }
            />
            <Route
              path="/landing-pages/:id/edit"
              element={
                <Suspense
                  fallback={
                    <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
                      Carregando editor visual...
                    </div>
                  }
                >
                  <LandingPageEditorPage />
                </Suspense>
              }
            />
            <Route
              path="/demos/:slug"

              element={
                <Suspense
                  fallback={
                    <div className="grid min-h-screen place-items-center bg-background text-sm text-muted-foreground">
                      Carregando demonstração...
                    </div>
                  }
                >
                  <LandingPageDemoPage />
                </Suspense>
              }
            />
            </Routes>
          </Suspense>
        </BrowserRouter>
        <Toaster position="bottom-right" richColors />
      </TooltipProvider>
    </QueryClientProvider>
  )
}
