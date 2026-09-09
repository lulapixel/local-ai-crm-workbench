import { useState, useCallback, useEffect, useMemo } from "react"
import type { LandingPageData, LandingPageService, LandingPageTestimonial, LandingPageFaq, LandingPageTrustItem } from "@/features/landing-pages/types"
import { landingPagesService, type LandingPageResponse } from "@/services/landingPagesService"
import type { EditorValidationErrors, SaveStatus } from "../editor-types"
import { toast } from "sonner"

export function sanitizePhoneNumber(phone: string): string {
  return phone.replace(/\D/g, "")
}

export function useLandingPageEditor(initialData: LandingPageResponse) {
  const [lpResponse, setLpResponse] = useState<LandingPageResponse>(initialData)
  const [originalSpec, setOriginalSpec] = useState<LandingPageData>(initialData.spec)
  const [draftSpec, setDraftSpec] = useState<LandingPageData>(initialData.spec)
  const [saveStatus, setSaveStatus] = useState<SaveStatus>("clean")
  const [validationErrors, setValidationErrors] = useState<EditorValidationErrors>({})
  const [isSaving, setIsSaving] = useState(false)

  // Sincronizar se o initialData mudar
  useEffect(() => {
    setLpResponse(initialData)
    setOriginalSpec(initialData.spec)
    setDraftSpec(initialData.spec)
  }, [initialData])

  // Comparação de alterações
  const isDirty = useMemo(() => {
    return JSON.stringify(originalSpec) !== JSON.stringify(draftSpec)
  }, [originalSpec, draftSpec])

  useEffect(() => {
    if (saveStatus !== "saving") {
      setSaveStatus(isDirty ? "dirty" : "clean")
    }
  }, [isDirty, saveStatus])

  // Helper para atualizar parcialmente o draftSpec
  const updateDraft = useCallback((updater: (prev: LandingPageData) => LandingPageData) => {
    setDraftSpec((prev) => updater(prev))
  }, [])

  // Validação frontend
  const validate = useCallback((): boolean => {
    const errors: EditorValidationErrors = {}

    if (!draftSpec.hero.title?.trim()) {
      errors["hero.title"] = "O título principal não pode ficar vazio."
    }

    if (!draftSpec.contact.whatsappNumber?.trim()) {
      errors["contact.whatsappNumber"] = "O número do WhatsApp é obrigatório."
    }

    draftSpec.services.forEach((service, index) => {
      if (!service.title?.trim()) {
        errors[`services.${index}.title`] = `O serviço #${index + 1} precisa de um nome.`
      }
      if (service.priceFrom < 0) {
        errors[`services.${index}.priceFrom`] = `O preço do serviço #${index + 1} não pode ser negativo.`
      }
    })

    draftSpec.faqs.forEach((faq, index) => {
      if (!faq.question?.trim()) {
        errors[`faqs.${index}.question`] = `A pergunta da FAQ #${index + 1} não pode ficar em branco.`
      }
      if (!faq.answer?.trim()) {
        errors[`faqs.${index}.answer`] = `A resposta da FAQ #${index + 1} não pode ficar em branco.`
      }
    })

    if (!draftSpec.palette.background?.trim()) {
      errors["palette.background"] = "A cor de fundo é obrigatória."
    }
    if (!draftSpec.palette.accent?.trim()) {
      errors["palette.accent"] = "A cor de destaque é obrigatória."
    }

    setValidationErrors(errors)
    return Object.keys(errors).length === 0
  }, [draftSpec])

  // Descartar alterações
  const discardChanges = useCallback(() => {
    setDraftSpec(originalSpec)
    setValidationErrors({})
    setSaveStatus("clean")
    toast.info("Alterações descartadas.")
  }, [originalSpec])

  // Salvar via PATCH
  const saveChanges = useCallback(async () => {
    if (!validate()) {
      toast.error("Existem erros de validação no formulário.")
      return false
    }

    // Normalização antes do envio (ex: whatsapp)
    const sanitizedSpec: LandingPageData = {
      ...draftSpec,
      contact: {
        ...draftSpec.contact,
        whatsappNumber: sanitizePhoneNumber(draftSpec.contact.whatsappNumber),
      },
    }

    setIsSaving(true)
    setSaveStatus("saving")

    try {
      const updated = await landingPagesService.atualizarSpec(lpResponse.id, sanitizedSpec)
      setLpResponse(updated)
      setOriginalSpec(updated.spec)
      setDraftSpec(updated.spec)
      setSaveStatus("saved")
      toast.success("Landing Page salva com sucesso!")
      return true
    } catch (err) {
      console.error("Erro ao salvar LP:", err)
      setSaveStatus("error")
      toast.error("Falha ao salvar as alterações. Tente novamente.")
      return false
    } finally {
      setIsSaving(false)
    }
  }, [draftSpec, lpResponse.id, validate])

  // Handlers específicos por seção
  const updateContentField = useCallback((field: string, value: string) => {
    updateDraft((prev) => {
      if (field.startsWith("hero.")) {
        const sub = field.replace("hero.", "") as keyof typeof prev.hero
        return { ...prev, hero: { ...prev.hero, [sub]: value } }
      }
      if (field.startsWith("finalCta.")) {
        const sub = field.replace("finalCta.", "") as keyof typeof prev.finalCta
        return { ...prev, finalCta: { ...prev.finalCta, [sub]: value } }
      }
      return prev
    })
  }, [updateDraft])

  const updateContactField = useCallback((field: keyof LandingPageData["contact"], value: string) => {
    updateDraft((prev) => ({
      ...prev,
      contact: { ...prev.contact, [field]: value },
    }))
  }, [updateDraft])

  const updateSeoField = useCallback((field: keyof LandingPageData["seo"], value: string) => {
    updateDraft((prev) => ({
      ...prev,
      seo: { ...prev.seo, [field]: value },
    }))
  }, [updateDraft])

  const updatePaletteColor = useCallback((key: keyof LandingPageData["palette"], hexValue: string) => {
    updateDraft((prev) => ({
      ...prev,
      palette: { ...prev.palette, [key]: hexValue },
    }))
  }, [updateDraft])

  // Service helpers
  const updateService = useCallback((index: number, updated: Partial<LandingPageService>) => {
    updateDraft((prev) => {
      const nextServices = [...prev.services]
      nextServices[index] = { ...nextServices[index], ...updated }
      return { ...prev, services: nextServices }
    })
  }, [updateDraft])

  const addService = useCallback(() => {
    updateDraft((prev) => ({
      ...prev,
      services: [
        ...prev.services,
        {
          id: `srv-${Date.now()}`,
          title: "Novo Serviço",
          shortDescription: "Descrição curta do serviço",
          description: "Descrição detalhada do serviço prestado com excelência.",
          imageUrl: "https://images.unsplash.com/photo-1570172619644-dfd03ed5d881?w=800&q=80",
          priceFrom: 150,
          duration: "60 min",
          highlight: "",
        },
      ],
    }))
  }, [updateDraft])

  const removeService = useCallback((index: number) => {
    updateDraft((prev) => ({
      ...prev,
      services: prev.services.filter((_, i) => i !== index),
    }))
  }, [updateDraft])

  const moveService = useCallback((index: number, direction: "up" | "down") => {
    updateDraft((prev) => {
      const targetIndex = direction === "up" ? index - 1 : index + 1
      if (targetIndex < 0 || targetIndex >= prev.services.length) return prev
      const nextServices = [...prev.services]
      const temp = nextServices[index]
      nextServices[index] = nextServices[targetIndex]
      nextServices[targetIndex] = temp
      return { ...prev, services: nextServices }
    })
  }, [updateDraft])

  // Social Proof helpers
  const updateTrustItem = useCallback((index: number, item: Partial<LandingPageTrustItem>) => {
    updateDraft((prev) => {
      const nextTrust = [...prev.trust]
      nextTrust[index] = { ...nextTrust[index], ...item }
      return { ...prev, trust: nextTrust }
    })
  }, [updateDraft])

  const addTrustItem = useCallback(() => {
    updateDraft((prev) => ({
      ...prev,
      trust: [...prev.trust, { label: "Métrica", value: "+100" }],
    }))
  }, [updateDraft])

  const removeTrustItem = useCallback((index: number) => {
    updateDraft((prev) => ({
      ...prev,
      trust: prev.trust.filter((_, i) => i !== index),
    }))
  }, [updateDraft])

  const updateTestimonial = useCallback((index: number, item: Partial<LandingPageTestimonial>) => {
    updateDraft((prev) => {
      const nextTestimonials = [...prev.testimonials]
      nextTestimonials[index] = { ...nextTestimonials[index], ...item }
      return { ...prev, testimonials: nextTestimonials }
    })
  }, [updateDraft])

  const addTestimonial = useCallback(() => {
    updateDraft((prev) => ({
      ...prev,
      testimonials: [
        ...prev.testimonials,
        {
          name: "Nome do Cliente",
          role: "Cliente Satisfeito",
          quote: "Excelente atendimento e ótimos resultados!",
          rating: 5,
        },
      ],
    }))
  }, [updateDraft])

  const removeTestimonial = useCallback((index: number) => {
    updateDraft((prev) => ({
      ...prev,
      testimonials: prev.testimonials.filter((_, i) => i !== index),
    }))
  }, [updateDraft])

  const updateFaq = useCallback((index: number, faq: Partial<LandingPageFaq>) => {
    updateDraft((prev) => {
      const nextFaqs = [...prev.faqs]
      nextFaqs[index] = { ...nextFaqs[index], ...faq }
      return { ...prev, faqs: nextFaqs }
    })
  }, [updateDraft])

  const addFaq = useCallback(() => {
    updateDraft((prev) => ({
      ...prev,
      faqs: [
        ...prev.faqs,
        {
          question: "Como funciona a contratação?",
          answer: "Entre em contato pelo WhatsApp para agendar uma avaliação inicial.",
        },
      ],
    }))
  }, [updateDraft])

  const removeFaq = useCallback((index: number) => {
    updateDraft((prev) => ({
      ...prev,
      faqs: prev.faqs.filter((_, i) => i !== index),
    }))
  }, [updateDraft])

  return {
    lpResponse,
    originalSpec,
    draftSpec,
    saveStatus,
    isDirty,
    isSaving,
    validationErrors,
    updateDraft,
    updateContentField,
    updateContactField,
    updateSeoField,
    updatePaletteColor,
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
    saveChanges,
    discardChanges,
  }
}
