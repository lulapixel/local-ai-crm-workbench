import { MessageCircleMore } from "lucide-react"

import type { LandingPageData } from "@/features/landing-pages/types"
import { buildWhatsAppUrl } from "@/features/landing-pages/utils"

type FloatingWhatsAppProps = {
  site: LandingPageData
  onClick?: () => void
}

export function FloatingWhatsApp({ site, onClick }: FloatingWhatsAppProps) {
  return (
    <a
      href={buildWhatsAppUrl(site.contact.whatsappNumber, site.contact.whatsappMessage)}
      target="_blank"
      rel="noreferrer"
      onClick={onClick}
      aria-label={`Conversar com ${site.brand.name} pelo WhatsApp`}
      className="fixed bottom-4 right-4 z-40 inline-flex min-h-[3.5rem] items-center gap-2 rounded-full bg-[#25d366] px-4 text-sm font-semibold text-[#071f10] shadow-2xl shadow-black/35 transition hover:-translate-y-1 sm:bottom-6 sm:right-6"
    >
      <MessageCircleMore className="size-5" />
      <span className="hidden sm:inline">Agendar pelo WhatsApp</span>
    </a>
  )
}
