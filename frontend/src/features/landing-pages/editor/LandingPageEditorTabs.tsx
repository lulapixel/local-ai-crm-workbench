import type { EditorTab } from "./editor-types"
import { FileText, Layers, ShieldCheck, Palette, Phone, Search } from "lucide-react"
import type { LandingPageData, LandingPageService, LandingPageTestimonial, LandingPageFaq, LandingPageTrustItem } from "@/features/landing-pages/types"
import type { EditorValidationErrors } from "./editor-types"

import { ContentFields } from "./fields/ContentFields"
import { ServicesFields } from "./fields/ServicesFields"
import { SocialProofFields } from "./fields/SocialProofFields"
import { VisualFields } from "./fields/VisualFields"
import { ContactFields } from "./fields/ContactFields"
import { SeoFields } from "./fields/SeoFields"

interface LandingPageEditorTabsProps {
  activeTab: EditorTab
  setActiveTab: (tab: EditorTab) => void
  draftSpec: LandingPageData
  errors: EditorValidationErrors
  isDirty?: boolean
  onOpenAiDialog?: (sectionKey: string, sectionLabel: string) => void
  updateContentField: (field: string, value: string) => void
  updateContactField: (field: keyof LandingPageData["contact"], value: string) => void
  updateSeoField: (field: keyof LandingPageData["seo"], value: string) => void
  updatePaletteColor: (key: keyof LandingPageData["palette"], hexValue: string) => void
  updateDraft: (updater: (prev: LandingPageData) => LandingPageData) => void
  updateService: (index: number, item: Partial<LandingPageService>) => void
  addService: () => void
  removeService: (index: number) => void
  moveService: (index: number, direction: "up" | "down") => void
  updateTrustItem: (index: number, item: Partial<LandingPageTrustItem>) => void
  addTrustItem: () => void
  removeTrustItem: (index: number) => void
  updateTestimonial: (index: number, item: Partial<LandingPageTestimonial>) => void
  addTestimonial: () => void
  removeTestimonial: (index: number) => void
  updateFaq: (index: number, faq: Partial<LandingPageFaq>) => void
  addFaq: () => void
  removeFaq: (index: number) => void
}

const tabsConfig: Array<{ id: EditorTab; label: string; icon: typeof FileText }> = [
  { id: "content", label: "Conteúdo", icon: FileText },
  { id: "services", label: "Serviços", icon: Layers },
  { id: "social-proof", label: "Prova social", icon: ShieldCheck },
  { id: "visual", label: "Visual", icon: Palette },
  { id: "contact", label: "Contato", icon: Phone },
  { id: "seo", label: "SEO", icon: Search },
]

export function LandingPageEditorTabs({
  activeTab,
  setActiveTab,
  draftSpec,
  errors,
  isDirty,
  onOpenAiDialog,
  updateContentField,
  updateContactField,
  updateSeoField,
  updatePaletteColor,
  updateDraft,
  updateService,
  addService,
  removeService,
  moveService,
  updateTrustItem,
  addTrustItem,
  removeTrustItem,
  updateTestimonial,
  addTestimonial,
  removeTestimonial,
  updateFaq,
  addFaq,
  removeFaq,
}: LandingPageEditorTabsProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Tab Navigation */}
      <div className="flex overflow-x-auto border-b border-border bg-muted/30 px-3 py-1.5 scrollbar-none">
        <div className="flex gap-1">
          {tabsConfig.map((tab) => {
            const Icon = tab.icon
            const isActive = activeTab === tab.id
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? "bg-background text-foreground shadow-sm"
                    : "text-muted-foreground hover:text-foreground hover:bg-background/50"
                }`}
              >
                <Icon className="size-3.5" />
                {tab.label}
              </button>
            )
          })}
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5">
        {activeTab === "content" && (
          <ContentFields
            draftSpec={draftSpec}
            updateContentField={updateContentField}
            errors={errors}
            isDirty={isDirty}
            onOpenAiDialog={onOpenAiDialog}
          />
        )}

        {activeTab === "services" && (
          <ServicesFields
            draftSpec={draftSpec}
            updateService={updateService}
            addService={addService}
            removeService={removeService}
            moveService={moveService}
            errors={errors}
            isDirty={isDirty}
            onOpenAiDialog={onOpenAiDialog}
          />
        )}

        {activeTab === "social-proof" && (
          <SocialProofFields
            draftSpec={draftSpec}
            updateTrustItem={updateTrustItem}
            addTrustItem={addTrustItem}
            removeTrustItem={removeTrustItem}
            updateTestimonial={updateTestimonial}
            addTestimonial={addTestimonial}
            removeTestimonial={removeTestimonial}
            updateFaq={updateFaq}
            addFaq={addFaq}
            removeFaq={removeFaq}
            errors={errors}
            isDirty={isDirty}
            onOpenAiDialog={onOpenAiDialog}
          />
        )}


        {activeTab === "visual" && (
          <VisualFields
            draftSpec={draftSpec}
            updatePaletteColor={updatePaletteColor}
            updateDraft={updateDraft}
            errors={errors}
          />
        )}

        {activeTab === "contact" && (
          <ContactFields
            draftSpec={draftSpec}
            updateContactField={updateContactField}
            errors={errors}
          />
        )}

        {activeTab === "seo" && (
          <SeoFields
            draftSpec={draftSpec}
            updateSeoField={updateSeoField}
            updateDraft={updateDraft}
            errors={errors}
          />
        )}
      </div>
    </div>
  )
}
