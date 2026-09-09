import type { LandingPageData } from "@/features/landing-pages/types"

type TrustBarProps = {
  site: LandingPageData
}

export function TrustBar({ site }: TrustBarProps) {
  return (
    <section className="border-b border-white/10 bg-white/[0.025] px-5 py-8 sm:px-8 lg:px-12">
      <div className="mx-auto grid max-w-7xl grid-cols-2 gap-6 sm:grid-cols-4">
        {site.trust.map((item) => (
          <div key={item.label} className="text-center sm:text-left">
            <strong className="block text-2xl font-medium tracking-[-0.04em] text-[var(--lp-text)] sm:text-3xl">
              {item.value}
            </strong>
            <span className="mt-1 block text-xs uppercase tracking-[0.14em] text-[var(--lp-muted)]">
              {item.label}
            </span>
          </div>
        ))}
      </div>
    </section>
  )
}
