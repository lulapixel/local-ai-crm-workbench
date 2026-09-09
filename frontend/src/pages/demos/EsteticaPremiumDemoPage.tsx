import { useEffect } from "react"

import { LandingPageTemplate } from "@/features/landing-pages/LandingPageTemplate"
import { esteticaPremiumSite } from "@/features/landing-pages/templates/estetica-premium/site"

export function EsteticaPremiumDemoPage() {
  useEffect(() => {
    const previousTitle = document.title
    const descriptionMeta = document.querySelector<HTMLMetaElement>('meta[name="description"]')
    const previousDescription = descriptionMeta?.content

    document.title = esteticaPremiumSite.seo.title
    if (descriptionMeta) {
      descriptionMeta.content = esteticaPremiumSite.seo.description
    }

    return () => {
      document.title = previousTitle
      if (descriptionMeta && previousDescription !== undefined) {
        descriptionMeta.content = previousDescription
      }
    }
  }, [])

  return <LandingPageTemplate site={esteticaPremiumSite} />
}
