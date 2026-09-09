export type LandingPagePalette = {
  background: string
  surface: string
  accent: string
  accentStrong: string
  text: string
  muted: string
}

export type LandingPageService = {
  id: string
  title: string
  shortDescription: string
  description: string
  imageUrl: string
  priceFrom: number
  duration: string
  highlight?: string
}

export type LandingPageTestimonial = {
  name: string
  role: string
  quote: string
  rating: number
  avatarUrl?: string
}

export type LandingPageFaq = {
  question: string
  answer: string
}

export type LandingPageTrustItem = {
  label: string
  value: string
}

export type LandingPageData = {
  slug: string
  brand: {
    name: string
    eyebrow: string
    logoUrl?: string
  }
  seo: {
    title: string
    description: string
  }
  palette: LandingPagePalette
  contact: {
    whatsappNumber: string
    whatsappMessage: string
    city: string
    instagram?: string
  }
  hero: {
    badge: string
    title: string
    highlightedText: string
    description: string
    primaryCta: string
    secondaryCta: string
    imageUrl: string
    imageAlt: string
    availabilityLabel: string
  }
  trust: LandingPageTrustItem[]
  services: LandingPageService[]
  testimonials: LandingPageTestimonial[]
  faqs: LandingPageFaq[]
  budget: {
    title: string
    description: string
    basePrice: number
    consultationLabel: string
  }
  finalCta: {
    title: string
    description: string
    buttonLabel: string
  }
}
