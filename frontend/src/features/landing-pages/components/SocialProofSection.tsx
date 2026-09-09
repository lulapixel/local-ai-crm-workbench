import { Star } from "lucide-react"

import type { LandingPageData } from "@/features/landing-pages/types"

type SocialProofSectionProps = {
  site: LandingPageData
}

export function SocialProofSection({ site }: SocialProofSectionProps) {
  return (
    <>
      {site.testimonials.length > 0 ? (
        <section className="px-5 py-20 sm:px-8 lg:px-12 lg:py-28">
          <div className="mx-auto max-w-7xl">
            <div className="max-w-2xl">
              <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--lp-accent)]">
                Experiências reais
              </p>
              <h2 className="mt-4 text-balance text-4xl font-medium tracking-[-0.045em] text-[var(--lp-text)] sm:text-5xl">
                Confiança construída em cada atendimento.
              </h2>
            </div>

            <div className="mt-10 grid gap-4 lg:grid-cols-3">
              {site.testimonials.map((testimonial) => (
                <article
                  key={testimonial.name}
                  className="rounded-[1.5rem] border border-white/10 bg-[var(--lp-surface)] p-6 sm:p-7"
                >
                  <div className="flex gap-1 text-[var(--lp-accent)]" aria-label={`${testimonial.rating} estrelas`}>
                    {Array.from({ length: testimonial.rating }).map((_, index) => (
                      <Star key={index} className="size-4 fill-current" />
                    ))}
                  </div>
                  <blockquote className="mt-5 text-lg leading-8 text-[var(--lp-text)]">
                    “{testimonial.quote}”
                  </blockquote>
                  <footer className="mt-7 border-t border-white/10 pt-5">
                    <strong className="block text-sm font-medium text-[var(--lp-text)]">
                      {testimonial.name}
                    </strong>
                    <span className="mt-1 block text-xs text-[var(--lp-muted)]">
                      {testimonial.role}
                    </span>
                  </footer>
                </article>
              ))}
            </div>
          </div>
        </section>
      ) : null}

      <section className="px-5 pb-20 sm:px-8 lg:px-12 lg:pb-28">
        <div className="mx-auto grid max-w-7xl gap-10 lg:grid-cols-[0.75fr_1.25fr]">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-[var(--lp-accent)]">
              Dúvidas frequentes
            </p>
            <h2 className="mt-4 text-balance text-4xl font-medium tracking-[-0.045em] text-[var(--lp-text)] sm:text-5xl">
              Antes de agendar.
            </h2>
          </div>

          <div className="divide-y divide-white/10 border-y border-white/10">
            {site.faqs.map((faq) => (
              <details key={faq.question} className="group py-5">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-5 text-base font-medium text-[var(--lp-text)]">
                  {faq.question}
                  <span className="grid size-7 shrink-0 place-items-center rounded-full border border-white/15 text-lg text-[var(--lp-accent)] transition group-open:rotate-45">
                    +
                  </span>
                </summary>
                <p className="max-w-2xl pb-1 pt-4 text-sm leading-6 text-[var(--lp-muted)]">
                  {faq.answer}
                </p>
              </details>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}
