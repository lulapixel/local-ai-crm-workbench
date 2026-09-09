import { motion } from "framer-motion"
import { ArrowRight, CalendarCheck2, MapPin, Sparkles } from "lucide-react"

import type { LandingPageData } from "@/features/landing-pages/types"
import { buildWhatsAppUrl } from "@/features/landing-pages/utils"

type HeroSectionProps = {
  site: LandingPageData
  onWhatsAppClick?: () => void
}

export function HeroSection({ site, onWhatsAppClick }: HeroSectionProps) {
  const whatsappUrl = buildWhatsAppUrl(
    site.contact.whatsappNumber,
    site.contact.whatsappMessage,
  )

  return (
    <section className="relative isolate min-h-screen overflow-hidden border-b border-white/10 px-5 pb-16 pt-5 sm:px-8 lg:px-12">
      <div className="pointer-events-none absolute inset-0 -z-10 bg-[radial-gradient(circle_at_82%_18%,color-mix(in_srgb,var(--lp-accent)_22%,transparent),transparent_34%),radial-gradient(circle_at_10%_90%,color-mix(in_srgb,var(--lp-accent-strong)_16%,transparent),transparent_36%)]" />

      <header className="mx-auto flex max-w-7xl items-center justify-between">
        <a href="#inicio" className="flex items-center gap-3" aria-label={site.brand.name}>
          {site.brand.logoUrl ? (
            <img
              src={site.brand.logoUrl}
              alt={site.brand.name}
              className="h-10 w-auto object-contain"
            />
          ) : (
            <span className="grid size-10 place-items-center rounded-full border border-[var(--lp-accent)]/45 bg-white/5 font-serif text-lg text-[var(--lp-accent)]">
              {site.brand.name.charAt(0)}
            </span>
          )}
          <span>
            <strong className="block text-sm font-medium tracking-[0.18em] text-[var(--lp-text)] uppercase">
              {site.brand.name}
            </strong>
            <span className="hidden text-xs text-[var(--lp-muted)] sm:block">
              {site.brand.eyebrow}
            </span>
          </span>
        </a>

        <a
          href={whatsappUrl}
          target="_blank"
          rel="noreferrer"
          onClick={onWhatsAppClick}
          className="rounded-full border border-white/15 bg-white/7 px-4 py-2.5 text-sm font-medium text-[var(--lp-text)] backdrop-blur transition hover:border-[var(--lp-accent)]/50 hover:bg-white/12"
        >
          Falar com a equipe
        </a>
      </header>

      <div id="inicio" className="mx-auto grid max-w-7xl items-center gap-12 pb-4 pt-16 lg:grid-cols-[1.04fr_0.96fr] lg:gap-16 lg:pt-20">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.65, ease: "easeOut" }}
        >
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[var(--lp-accent)]/30 bg-[var(--lp-accent)]/8 px-3 py-1.5 text-xs font-medium text-[var(--lp-accent)]">
            <Sparkles className="size-3.5" />
            {site.hero.badge}
          </div>

          <h1 className="max-w-3xl text-balance text-5xl font-medium leading-[0.96] tracking-[-0.055em] text-[var(--lp-text)] sm:text-6xl lg:text-7xl xl:text-[5.5rem]">
            {site.hero.title}{" "}
            <span className="font-serif font-normal italic text-[var(--lp-accent)]">
              {site.hero.highlightedText}
            </span>
          </h1>

          <p className="mt-7 max-w-xl text-pretty text-base leading-7 text-[var(--lp-muted)] sm:text-lg">
            {site.hero.description}
          </p>

          <div className="mt-9 flex flex-col gap-3 sm:flex-row">
            <a
              href={whatsappUrl}
              target="_blank"
              rel="noreferrer"
              onClick={onWhatsAppClick}
              className="inline-flex min-h-13 items-center justify-center gap-2 rounded-full bg-[var(--lp-accent)] px-6 text-sm font-semibold text-[#25151c] transition hover:-translate-y-0.5 hover:bg-[var(--lp-accent-strong)]"
            >
              {site.hero.primaryCta}
              <ArrowRight className="size-4" />
            </a>
            <a
              href="#tratamentos"
              className="inline-flex min-h-13 items-center justify-center rounded-full border border-white/15 px-6 text-sm font-medium text-[var(--lp-text)] transition hover:border-white/30 hover:bg-white/5"
            >
              {site.hero.secondaryCta}
            </a>
          </div>

          <div className="mt-9 flex flex-wrap gap-x-6 gap-y-3 text-sm text-[var(--lp-muted)]">
            <span className="inline-flex items-center gap-2">
              <CalendarCheck2 className="size-4 text-[var(--lp-accent)]" />
              {site.hero.availabilityLabel}
            </span>
            <span className="inline-flex items-center gap-2">
              <MapPin className="size-4 text-[var(--lp-accent)]" />
              {site.contact.city}
            </span>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.96 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.75, delay: 0.12, ease: "easeOut" }}
          className="relative mx-auto w-full max-w-xl lg:max-w-none"
        >
          <div className="relative aspect-[4/5] overflow-hidden rounded-[2rem] border border-white/10 bg-[var(--lp-surface)] shadow-2xl shadow-black/40 sm:aspect-[5/6]">
            <img
              src={site.hero.imageUrl}
              alt={site.hero.imageAlt}
              className="h-full w-full object-cover"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/65 via-transparent to-black/10" />
          </div>

          <div className="absolute -bottom-5 left-4 right-4 rounded-2xl border border-white/15 bg-black/55 p-4 backdrop-blur-xl sm:left-8 sm:right-auto sm:w-72">
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--lp-accent)]">
              Atendimento direto
            </p>
            <p className="mt-2 text-sm leading-6 text-white/85">
              Consulte serviços e horários antes de se deslocar.
            </p>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
