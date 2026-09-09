import { useEffect, useRef, type CSSProperties } from "react"
import { ArrowRight } from "lucide-react"

import { BudgetSimulator } from "@/features/landing-pages/components/BudgetSimulator"
import { FloatingWhatsApp } from "@/features/landing-pages/components/FloatingWhatsApp"
import { HeroSection } from "@/features/landing-pages/components/HeroSection"
import { ServicesGallery } from "@/features/landing-pages/components/ServicesGallery"
import { SocialProofSection } from "@/features/landing-pages/components/SocialProofSection"
import { TrustBar } from "@/features/landing-pages/components/TrustBar"
import type { LandingPageData } from "@/features/landing-pages/types"
import { buildWhatsAppUrl } from "@/features/landing-pages/utils"
import { useTrackEvent } from "@/features/landing-pages/hooks/useTrackEvent"

type LandingPageTemplateProps = {
  site: LandingPageData
  slug?: string
  isPreview?: boolean
}

export function LandingPageTemplate({ site, slug, isPreview }: LandingPageTemplateProps) {
  const { trackEvent } = useTrackEvent(slug, isPreview)
  const trackedRef = useRef(false)

  useEffect(() => {
    if (!trackedRef.current) {
      trackedRef.current = true
      trackEvent("page_view")
    }
  }, [trackEvent])

  const themeStyle = {
    "--lp-background": site.palette.background,
    "--lp-surface": site.palette.surface,
    "--lp-accent": site.palette.accent,
    "--lp-accent-strong": site.palette.accentStrong,
    "--lp-text": site.palette.text,
    "--lp-muted": site.palette.muted,
    backgroundColor: site.palette.background,
    color: site.palette.text,
  } as CSSProperties

  const whatsappUrl = buildWhatsAppUrl(
    site.contact.whatsappNumber,
    site.contact.whatsappMessage,
  )

  return (
    <main style={themeStyle} className="min-h-screen bg-[var(--lp-background)] font-sans antialiased">
      <HeroSection site={site} onWhatsAppClick={() => trackEvent("whatsapp_click", { source: "hero" })} />
      <TrustBar site={site} />
      <ServicesGallery site={site} onServiceClick={(title) => trackEvent("service_open", { service: title })} />
      <BudgetSimulator
        site={site}
        onStart={() => trackEvent("simulator_start")}
        onComplete={() => trackEvent("simulator_complete")}
      />
      <SocialProofSection site={site} />

      <section className="px-5 pb-10 sm:px-8 lg:px-12">
        <div className="relative mx-auto max-w-7xl overflow-hidden rounded-[2rem] border border-[var(--lp-accent)]/25 bg-[var(--lp-accent)]/10 px-6 py-14 text-center sm:px-10 sm:py-18">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,color-mix(in_srgb,var(--lp-accent)_24%,transparent),transparent_55%)]" />
          <div className="relative mx-auto max-w-3xl">
            <h2 className="text-balance text-4xl font-medium tracking-[-0.05em] text-[var(--lp-text)] sm:text-6xl">
              {site.finalCta.title}
            </h2>
            <p className="mx-auto mt-5 max-w-2xl text-pretty text-base leading-7 text-[var(--lp-muted)]">
              {site.finalCta.description}
            </p>
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noreferrer"
              onClick={() => trackEvent("whatsapp_click", { source: "final_cta" })}
              className="mt-8 inline-flex min-h-[3.25rem] items-center justify-center gap-2 rounded-full bg-[var(--lp-accent)] px-6 text-sm font-semibold text-[#25151c] transition hover:-translate-y-0.5 hover:bg-[var(--lp-accent-strong)]"
            >
              {site.finalCta.buttonLabel}
              <ArrowRight className="size-4" />
            </a>
          </div>
        </div>
      </section>

      <footer className="px-5 pb-24 pt-8 sm:px-8 lg:px-12">
        <div className="mx-auto flex max-w-7xl flex-col gap-3 border-t border-white/10 pt-7 text-xs text-[var(--lp-muted)] sm:flex-row sm:items-center sm:justify-between">
          <span>{site.brand.name} · {site.contact.city}</span>
          <span>Consulte disponibilidade pelo WhatsApp</span>
        </div>
      </footer>

      <FloatingWhatsApp site={site} onClick={() => trackEvent("whatsapp_click", { source: "floating_button" })} />
    </main>
  )
}
