import type {
  LandingPageData,
  LandingPageTrustItem,
  LandingPageTestimonial,
  LandingPageFaq,
} from "@/features/landing-pages/types"
import type { EditorValidationErrors } from "../editor-types"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { AlertCircle, Plus, Trash2, Sparkles } from "lucide-react"

interface SocialProofFieldsProps {
  draftSpec: LandingPageData
  updateTrustItem: (index: number, item: Partial<LandingPageTrustItem>) => void
  addTrustItem: () => void
  removeTrustItem: (index: number) => void
  updateTestimonial: (index: number, item: Partial<LandingPageTestimonial>) => void
  addTestimonial: () => void
  removeTestimonial: (index: number) => void
  updateFaq: (index: number, faq: Partial<LandingPageFaq>) => void
  addFaq: () => void
  removeFaq: (index: number) => void
  errors: EditorValidationErrors
  isDirty?: boolean
  onOpenAiDialog?: (sectionKey: string, sectionLabel: string) => void
}

export function SocialProofFields({
  draftSpec,
  updateTrustItem,
  addTrustItem,
  removeTrustItem,
  updateTestimonial,
  addTestimonial,
  removeTestimonial,
  updateFaq,
  addFaq,
  removeFaq,
  errors,
  isDirty,
  onOpenAiDialog,
}: SocialProofFieldsProps) {
  return (
    <div className="space-y-6">
      {/* Warning Box */}
      <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 flex items-start gap-2.5 text-xs text-amber-200">
        <AlertCircle className="size-4 text-amber-400 shrink-0 mt-0.5" />
        <span>
          <strong>Aviso de conformidade:</strong> Use apenas depoimentos autorizados ou marque-os como demonstrativos.
        </span>
      </div>

      {/* Trust Bar Metrics */}
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b pb-2">
          <h3 className="text-sm font-semibold text-foreground">
            Métricas de Confiança (Trust Bar)
          </h3>
          <Button size="sm" variant="outline" onClick={addTrustItem} className="gap-1">
            <Plus className="size-3.5" />
            Adicionar Métrica
          </Button>
        </div>

        <div className="grid grid-cols-1 gap-3">
          {draftSpec.trust.map((item, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                value={item.value || ""}
                onChange={(e) => updateTrustItem(index, { value: e.target.value })}
                placeholder="Valor (ex: +5.000)"
                className="w-1/3"
              />
              <Input
                value={item.label || ""}
                onChange={(e) => updateTrustItem(index, { label: e.target.value })}
                placeholder="Rótulo (ex: Clientes Satisfeitos)"
                className="w-2/3"
              />
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="size-8 text-destructive shrink-0"
                onClick={() => removeTrustItem(index)}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </div>
          ))}
        </div>
      </div>

      {/* Testimonials */}
      <div className="space-y-4 pt-4 border-t">
        <div className="flex items-center justify-between border-b pb-2">
          <h3 className="text-sm font-semibold text-foreground">
            Depoimentos de Clientes ({draftSpec.testimonials.length})
          </h3>
          <Button size="sm" variant="outline" onClick={addTestimonial} className="gap-1">
            <Plus className="size-3.5" />
            Adicionar Depoimento
          </Button>
        </div>

        <div className="space-y-3">
          {draftSpec.testimonials.map((t, index) => (
            <div key={index} className="rounded-lg border border-border bg-card p-3 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-muted-foreground">
                  Depoimento #{index + 1}
                </span>
                <Button
                  type="button"
                  size="icon"
                  variant="ghost"
                  className="size-7 text-destructive"
                  onClick={() => removeTestimonial(index)}
                >
                  <Trash2 className="size-3.5" />
                </Button>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Nome
                  </label>
                  <Input
                    value={t.name || ""}
                    onChange={(e) => updateTestimonial(index, { name: e.target.value })}
                    placeholder="Ex: Dra. Mariana Costa"
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Cargo / Subtítulo
                  </label>
                  <Input
                    value={t.role || ""}
                    onChange={(e) => updateTestimonial(index, { role: e.target.value })}
                    placeholder="Ex: Paciente há 2 anos"
                  />
                </div>

                <div className="space-y-1 sm:col-span-2">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Depoimento (Citação)
                  </label>
                  <Textarea
                    value={t.quote || ""}
                    onChange={(e) => updateTestimonial(index, { quote: e.target.value })}
                    placeholder="Relato do cliente..."
                    rows={2}
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Avaliação (1 a 5 estrelas)
                  </label>
                  <Input
                    type="number"
                    min={1}
                    max={5}
                    value={t.rating ?? 5}
                    onChange={(e) =>
                      updateTestimonial(index, { rating: Number(e.target.value) || 5 })
                    }
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* FAQ */}
      <div className="space-y-4 pt-4 border-t">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
          <h3 className="text-sm font-semibold text-foreground">
            Perguntas Frequentes - FAQ ({draftSpec.faqs.length})
          </h3>
          <div className="flex items-center gap-2">
            {onOpenAiDialog && (
              <Button
                size="sm"
                variant="outline"
                disabled={isDirty}
                title={isDirty ? "Salve ou descarte suas alterações antes de usar a IA." : "Reescrever FAQ com IA"}
                onClick={() => onOpenAiDialog("faqs", "FAQ")}
                className="gap-1 text-xs border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
              >
                <Sparkles className="size-3.5 text-purple-400" />
                Reescrever FAQ com IA
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={addFaq} className="gap-1">
              <Plus className="size-3.5" />
              Adicionar Pergunta
            </Button>
          </div>
        </div>

        <div className="space-y-3">
          {draftSpec.faqs.map((faq, index) => {
            const qErr = errors[`faqs.${index}.question`]
            const aErr = errors[`faqs.${index}.answer`]

            return (
              <div key={index} className="rounded-lg border border-border bg-card p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-muted-foreground">
                    FAQ #{index + 1}
                  </span>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="size-7 text-destructive"
                    onClick={() => removeFaq(index)}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Pergunta *
                  </label>
                  <Input
                    value={faq.question || ""}
                    onChange={(e) => updateFaq(index, { question: e.target.value })}
                    placeholder="Ex: Como é feito o agendamento?"
                    className={qErr ? "border-destructive" : ""}
                  />
                  {qErr && <p className="text-xs text-destructive">{qErr}</p>}
                </div>

                <div className="space-y-1">
                  <label className="text-[11px] font-medium text-muted-foreground">
                    Resposta *
                  </label>
                  <Textarea
                    value={faq.answer || ""}
                    onChange={(e) => updateFaq(index, { answer: e.target.value })}
                    placeholder="Explicação clara e objetiva..."
                    rows={2}
                    className={aErr ? "border-destructive" : ""}
                  />
                  {aErr && <p className="text-xs text-destructive">{aErr}</p>}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
