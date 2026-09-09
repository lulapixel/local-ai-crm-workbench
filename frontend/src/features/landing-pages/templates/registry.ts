import type { ComponentType } from "react"
import { LandingPageTemplate } from "@/features/landing-pages/LandingPageTemplate"
import type { LandingPageData } from "@/features/landing-pages/types"

export type TemplateRendererProps = {
  site: LandingPageData
  slug?: string
  isPreview?: boolean
  onTrackEvent?: (eventType: any, metadata?: Record<string, string>) => void
}

export const landingPageTemplates: Record<
  string,
  ComponentType<TemplateRendererProps>
> = {
  "estetica-premium": LandingPageTemplate,
  "geral-conversao": LandingPageTemplate,
}

export function getTemplateRenderer(
  templateKey: string
): ComponentType<TemplateRendererProps> {
  return landingPageTemplates[templateKey] || LandingPageTemplate
}
