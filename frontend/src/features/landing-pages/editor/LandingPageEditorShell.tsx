import { useState } from "react"
import type { EditorTab, EditorValidationErrors, SaveStatus } from "./editor-types"
import type { LandingPageData, LandingPageService, LandingPageTestimonial, LandingPageFaq, LandingPageTrustItem } from "@/features/landing-pages/types"
import type { LandingPageResponse, LandingPageVersionSummary, LandingPageVersionDetail } from "@/services/landingPagesService"

import { LandingPageEditorHeader } from "./LandingPageEditorHeader"
import { LandingPageEditorTabs } from "./LandingPageEditorTabs"
import { LandingPageEditorPreview } from "./LandingPageEditorPreview"
import { AiRegenerationDialog, type AiTone } from "./components/AiRegenerationDialog"
import { VersionHistoryDrawer } from "./components/VersionHistoryDrawer"
import { VersionPreviewDialog } from "./components/VersionPreviewDialog"

interface LandingPageEditorShellProps {
  lpResponse: LandingPageResponse
  draftSpec: LandingPageData
  saveStatus: SaveStatus
  isDirty: boolean
  isSaving: boolean
  validationErrors: EditorValidationErrors
  onSave: () => void
  onDiscard: () => void
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
  // History and AI props
  historyVersions: LandingPageVersionSummary[]
  isLoadingHistory: boolean
  onRegenerateSection: (sections: string[], tone: AiTone, instruction: string) => Promise<boolean>
  onPreviewVersion: (version: number) => void
  onRestoreVersion: (version: number) => Promise<boolean>
  previewVersionDetail: LandingPageVersionDetail | null
  isLoadingVersionDetail: boolean
  previewVersionNumber: number | null
  onClosePreviewVersion: () => void
  isRestoring: boolean
}

export function LandingPageEditorShell({
  lpResponse,
  draftSpec,
  saveStatus,
  isDirty,
  isSaving,
  validationErrors,
  onSave,
  onDiscard,
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
  historyVersions,
  isLoadingHistory,
  onRegenerateSection,
  onPreviewVersion,
  onRestoreVersion,
  previewVersionDetail,
  isLoadingVersionDetail,
  previewVersionNumber,
  onClosePreviewVersion,
  isRestoring,
}: LandingPageEditorShellProps) {
  const [activeTab, setActiveTab] = useState<EditorTab>("content")
  const [isMobilePreviewOpen, setIsMobilePreviewOpen] = useState(false)
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)
  const [aiTarget, setAiTarget] = useState<{ key: string; label: string } | null>(null)

  const handleOpenAiDialog = (sectionKey: string, sectionLabel: string) => {
    setAiTarget({ key: sectionKey, label: sectionLabel })
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-background relative">
      <LandingPageEditorHeader
        lpResponse={lpResponse}
        saveStatus={saveStatus}
        isDirty={isDirty}
        isSaving={isSaving}
        onSave={onSave}
        onDiscard={onDiscard}
        onToggleMobilePreview={() => setIsMobilePreviewOpen(!isMobilePreviewOpen)}
        isMobilePreviewOpen={isMobilePreviewOpen}
        onOpenHistory={() => setIsHistoryOpen(true)}
      />

      <div className="flex flex-1 overflow-hidden relative">
        {/* Painel do Editor */}
        <div
          className={`flex flex-col border-r border-border bg-card w-full lg:w-[460px] shrink-0 h-full ${
            isMobilePreviewOpen ? "hidden lg:flex" : "flex"
          }`}
        >
          <LandingPageEditorTabs
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            draftSpec={draftSpec}
            errors={validationErrors}
            isDirty={isDirty}
            onOpenAiDialog={handleOpenAiDialog}
            updateContentField={updateContentField}
            updateContactField={updateContactField}
            updateSeoField={updateSeoField}
            updatePaletteColor={updatePaletteColor}
            updateDraft={updateDraft}
            updateService={updateService}
            addService={addService}
            removeService={removeService}
            moveService={moveService}
            updateTrustItem={updateTrustItem}
            addTrustItem={addTrustItem}
            removeTrustItem={removeTrustItem}
            updateTestimonial={updateTestimonial}
            addTestimonial={addTestimonial}
            removeTestimonial={removeTestimonial}
            updateFaq={updateFaq}
            addFaq={addFaq}
            removeFaq={removeFaq}
          />
        </div>

        {/* Painel de Preview em Tempo Real */}
        <div
          className={`flex-1 h-full overflow-hidden ${
            isMobilePreviewOpen ? "flex w-full" : "hidden lg:flex"
          }`}
        >
          <LandingPageEditorPreview draftSpec={draftSpec} />
        </div>
      </div>

      {/* AI Regeneration Dialog */}
      {aiTarget && (
        <AiRegenerationDialog
          isOpen={Boolean(aiTarget)}
          onClose={() => setAiTarget(null)}
          sectionKey={aiTarget.key}
          sectionLabel={aiTarget.label}
          onRegenerate={onRegenerateSection}
        />
      )}

      {/* Version History Drawer */}
      <VersionHistoryDrawer
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        versions={historyVersions}
        isLoading={isLoadingHistory}
        onPreviewVersion={onPreviewVersion}
        onRestoreVersion={onRestoreVersion}
        isRestoring={isRestoring}
      />

      {/* Version Preview Dialog */}
      <VersionPreviewDialog
        isOpen={previewVersionNumber !== null}
        onClose={onClosePreviewVersion}
        versionDetail={previewVersionDetail}
        isLoading={isLoadingVersionDetail}
        onRestoreVersion={onRestoreVersion}
        isRestoring={isRestoring}
      />
    </div>
  )
}
