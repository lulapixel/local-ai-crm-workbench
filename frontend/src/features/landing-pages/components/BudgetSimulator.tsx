import { useMemo, useState } from "react"
import { Check, MessageCircleMore, Sparkles } from "lucide-react"

import type { LandingPageData } from "@/features/landing-pages/types"
import { buildWhatsAppUrl, formatCurrency } from "@/features/landing-pages/utils"

type BudgetSimulatorProps = {
  site: LandingPageData
  onStart?: () => void
  onComplete?: () => void
}

export function BudgetSimulator({ site, onStart, onComplete }: BudgetSimulatorProps) {
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [hasStarted, setHasStarted] = useState(false)

  const selectedServices = useMemo(
    () => site.services.filter((service) => selectedIds.includes(service.id)),
    [selectedIds, site.services],
  )

  const estimatedTotal = useMemo(
    () =>
      site.budget.basePrice +
      selectedServices.reduce((total, service) => total + service.priceFrom, 0),
    [selectedServices, site.budget.basePrice],
  )
  const hasKnownPricing = site.budget.basePrice > 0 || selectedServices.some((service) => service.priceFrom > 0)
  const hasUnknownPricing = site.budget.basePrice <= 0 || selectedServices.some((service) => service.priceFrom <= 0)
  const hasPartialPricing = hasKnownPricing && hasUnknownPricing
  const formatOptionalPrice = (price: number) => (price > 0 ? formatCurrency(price) : "Sob consulta")

  const whatsappMessage = useMemo(() => {
    const interests = selectedServices.length
      ? selectedServices.map((service) => service.title).join(", ")
      : "uma avaliação personalizada"

    const priceContext = !hasKnownPricing
      ? "Gostaria de confirmar valores e disponibilidade."
      : hasPartialPricing
        ? `A estimativa parcial exibida foi ${formatCurrency(estimatedTotal)}. Há valores sob consulta.`
        : `O total estimado exibido foi ${formatCurrency(estimatedTotal)}.`

    return `${site.contact.whatsappMessage}\n\nTenho interesse em: ${interests}. ${priceContext}`
  }, [estimatedTotal, hasKnownPricing, hasPartialPricing, selectedServices, site.contact.whatsappMessage])

  function toggleService(serviceId: string) {
    if (!hasStarted) {
      setHasStarted(true)
      onStart?.()
    }
    setSelectedIds((current) =>
      current.includes(serviceId)
        ? current.filter((id) => id !== serviceId)
        : [...current, serviceId],
    )
  }

  return (
    <section id="simulador" className="px-5 py-20 sm:px-8 lg:px-12 lg:py-28">
      <div className="mx-auto grid max-w-7xl overflow-hidden rounded-[2rem] border border-white/10 bg-[var(--lp-surface)] lg:grid-cols-[1.1fr_0.9fr]">
        <div className="p-6 sm:p-9 lg:p-12">
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.22em] text-[var(--lp-accent)]">
            <Sparkles className="size-4" />
            Seleção de serviços
          </div>
          <h2 className="mt-4 max-w-xl text-balance text-4xl font-medium tracking-[-0.045em] text-[var(--lp-text)] sm:text-5xl">
            {site.budget.title}
          </h2>
          <p className="mt-5 max-w-2xl text-sm leading-6 text-[var(--lp-muted)] sm:text-base">
            {site.budget.description}
          </p>

          <div className="mt-8 grid gap-3 sm:grid-cols-2">
            {site.services.map((service) => {
              const selected = selectedIds.includes(service.id)

              return (
                <button
                  key={service.id}
                  type="button"
                  onClick={() => toggleService(service.id)}
                  aria-pressed={selected}
                  className={`flex min-h-24 items-start justify-between gap-4 rounded-2xl border p-4 text-left transition ${
                    selected
                      ? "border-[var(--lp-accent)] bg-[var(--lp-accent)]/10"
                      : "border-white/10 bg-white/[0.025] hover:border-white/20 hover:bg-white/5"
                  }`}
                >
                  <span>
                    <strong className="block text-sm font-medium text-[var(--lp-text)]">
                      {service.title}
                    </strong>
                    <span className="mt-1 block text-xs leading-5 text-[var(--lp-muted)]">
                      {formatOptionalPrice(service.priceFrom)}
                    </span>
                  </span>
                  <span
                    className={`grid size-6 shrink-0 place-items-center rounded-full border ${
                      selected
                        ? "border-[var(--lp-accent)] bg-[var(--lp-accent)] text-[#25151c]"
                        : "border-white/20 text-transparent"
                    }`}
                  >
                    <Check className="size-3.5" />
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        <aside className="flex flex-col justify-between border-t border-white/10 bg-black/25 p-6 sm:p-9 lg:border-l lg:border-t-0 lg:p-12">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-[var(--lp-muted)]">
              {!hasKnownPricing ? "Consulta de valores" : hasPartialPricing ? "Estimativa parcial" : "Estimativa inicial"}
            </p>
            <p className="mt-3 text-5xl font-medium tracking-[-0.06em] text-[var(--lp-text)] sm:text-6xl">
              {hasKnownPricing ? formatCurrency(estimatedTotal) : "Sob consulta"}
            </p>
            <p className="mt-3 text-sm leading-6 text-[var(--lp-muted)]">
              Inclui {site.budget.consultationLabel.toLowerCase()}
              {selectedServices.length
                ? ` e ${selectedServices.length} serviço${selectedServices.length > 1 ? "s" : ""} selecionado${selectedServices.length > 1 ? "s" : ""}.`
                : "."}
            </p>
          </div>

          <div className="mt-12">
            <div className="mb-5 space-y-2 border-y border-white/10 py-5 text-sm">
              <div className="flex justify-between gap-4 text-[var(--lp-muted)]">
                <span>{site.budget.consultationLabel}</span>
                <span>{formatOptionalPrice(site.budget.basePrice)}</span>
              </div>
              {selectedServices.map((service) => (
                <div key={service.id} className="flex justify-between gap-4 text-[var(--lp-muted)]">
                  <span>{service.title}</span>
                  <span>{formatOptionalPrice(service.priceFrom)}</span>
                </div>
              ))}
            </div>

            <a
              href={buildWhatsAppUrl(site.contact.whatsappNumber, whatsappMessage)}
              target="_blank"
              rel="noreferrer"
              onClick={onComplete}
              className="inline-flex min-h-[3.25rem] w-full items-center justify-center gap-2 rounded-full bg-[var(--lp-accent)] px-5 text-sm font-semibold text-[#25151c] transition hover:-translate-y-0.5 hover:bg-[var(--lp-accent-strong)]"
            >
              <MessageCircleMore className="size-4" />
              Enviar seleção pelo WhatsApp
            </a>
            <p className="mt-3 text-center text-[0.7rem] leading-5 text-[var(--lp-muted)]">
              {!hasKnownPricing
                ? "Valores e disponibilidade são confirmados diretamente no atendimento."
                : hasPartialPricing
                  ? "Estimativa parcial: há valores sob consulta que serão confirmados no atendimento."
                  : "Valores demonstrativos. A proposta final depende da confirmação no atendimento."}
            </p>
          </div>
        </aside>
      </div>
    </section>
  )
}
