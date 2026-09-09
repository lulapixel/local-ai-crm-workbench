import type { LandingPageData } from "@/features/landing-pages/types"
import { LandingPageTemplate } from "@/features/landing-pages/LandingPageTemplate"

interface LandingPageEditorPreviewProps {
  draftSpec: LandingPageData
}

export function LandingPageEditorPreview({ draftSpec }: LandingPageEditorPreviewProps) {
  return (
    <div className="h-full w-full overflow-y-auto bg-neutral-950 relative">
      <div className="mx-auto min-h-full max-w-7xl shadow-2xl transition-all">
        <LandingPageTemplate site={draftSpec} />
      </div>
    </div>
  )
}
