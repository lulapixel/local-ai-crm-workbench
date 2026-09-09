import { motion } from "framer-motion"
import { ArrowUpRight, Clock3 } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import type { LandingPageData } from "@/features/landing-pages/types"
import { formatCurrency } from "@/features/landing-pages/utils"

type ServicesGalleryProps = {
  site: LandingPageData
  onServiceClick?: (title: string) => void
}

export function ServicesGallery({ site, onServiceClick }: ServicesGalleryProps) {
  const formatServicePrice = (price: number) =>
    price > 0 ? `A partir de ${formatCurrency(price)}` : "Valor sob consulta"

  return (
    <section id="tratamentos" className="px-5 py-20 sm:px-8 lg:px-12 lg:py-28">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-6 lg:grid-cols-[0.72fr_1.28fr] lg:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--lp-accent)]">
              Serviços
            </p>
            <h2 className="mt-4 max-w-xl text-balance text-4xl font-medium tracking-[-0.045em] text-[var(--lp-text)] sm:text-5xl">
              Opções para o que você precisa.
            </h2>
          </div>
          <p className="max-w-2xl text-base leading-7 text-[var(--lp-muted)] lg:justify-self-end">
            Conheça os serviços disponíveis. Detalhes, valores e disponibilidade são confirmados diretamente no atendimento.
          </p>
        </div>

        <div className="mt-12 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {site.services.map((service, index) => (
            <Dialog key={service.id}>
              <DialogTrigger asChild>
                <motion.button
                  type="button"
                  onClick={() => onServiceClick?.(service.title)}
                  initial={{ opacity: 0, y: 18 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true, amount: 0.25 }}
                  transition={{ duration: 0.45, delay: index * 0.06 }}
                  className="group relative min-h-[29rem] overflow-hidden rounded-[1.5rem] border border-white/10 bg-[var(--lp-surface)] text-left"
                >
                  <img
                    src={service.imageUrl}
                    alt={service.title}
                    loading="lazy"
                    className="absolute inset-0 h-full w-full object-cover transition duration-700 group-hover:scale-105"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black via-black/35 to-transparent" />

                  {service.highlight ? (
                    <span className="absolute left-4 top-4 rounded-full bg-[var(--lp-accent)] px-3 py-1 text-[0.68rem] font-bold uppercase tracking-[0.14em] text-[#25151c]">
                      {service.highlight}
                    </span>
                  ) : null}

                  <div className="absolute inset-x-0 bottom-0 p-5">
                    <div className="mb-3 flex items-center justify-between gap-3">
                      <span className="text-xs text-white/65">{formatServicePrice(service.priceFrom)}</span>
                      <span className="grid size-9 place-items-center rounded-full border border-white/20 bg-white/10 text-white transition group-hover:bg-white group-hover:text-black">
                        <ArrowUpRight className="size-4" />
                      </span>
                    </div>
                    <h3 className="text-xl font-medium text-white">{service.title}</h3>
                    <p className="mt-2 text-sm leading-6 text-white/70">
                      {service.shortDescription}
                    </p>
                  </div>
                </motion.button>
              </DialogTrigger>

              <DialogContent className="max-h-[90vh] overflow-y-auto border-white/10 bg-[#151116] p-0 text-white sm:max-w-2xl">
                <div className="aspect-[16/9] overflow-hidden rounded-t-xl">
                  <img
                    src={service.imageUrl}
                    alt={service.title}
                    className="h-full w-full object-cover"
                  />
                </div>
                <DialogHeader className="p-6 pt-2">
                  <DialogTitle className="text-2xl">{service.title}</DialogTitle>
                  <DialogDescription className="text-sm leading-6 text-white/65">
                    {service.description}
                  </DialogDescription>
                  <div className="flex flex-wrap gap-3 pt-3 text-sm">
                    <span className="rounded-full border border-white/10 bg-white/5 px-3 py-2 text-white/80">
                      {formatServicePrice(service.priceFrom)}
                    </span>
                    <span className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-2 text-white/80">
                      <Clock3 className="size-4 text-[var(--lp-accent)]" />
                      {service.duration}
                    </span>
                  </div>
                </DialogHeader>
              </DialogContent>
            </Dialog>
          ))}
        </div>
      </div>
    </section>
  )
}
