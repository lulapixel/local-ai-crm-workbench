import type { LandingPageData, LandingPageService } from "@/features/landing-pages/types"
import type { EditorValidationErrors } from "../editor-types"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { ArrowUp, ArrowDown, Trash2, Plus, Sparkles } from "lucide-react"

interface ServicesFieldsProps {
  draftSpec: LandingPageData
  updateService: (index: number, item: Partial<LandingPageService>) => void
  addService: () => void
  removeService: (index: number) => void
  moveService: (index: number, direction: "up" | "down") => void
  errors: EditorValidationErrors
  isDirty?: boolean
  onOpenAiDialog?: (sectionKey: string, sectionLabel: string) => void
}

export function ServicesFields({
  draftSpec,
  updateService,
  addService,
  removeService,
  moveService,
  errors,
  isDirty,
  onOpenAiDialog,
}: ServicesFieldsProps) {
  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b pb-2">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Catálogo de Serviços ({draftSpec.services.length})
          </h3>
          <p className="text-xs text-muted-foreground">
            Gerencie os serviços oferecidos e ajuste a ordem de exibição.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {onOpenAiDialog && (
            <Button
              size="sm"
              variant="outline"
              disabled={isDirty}
              title={isDirty ? "Salve ou descarte suas alterações antes de usar a IA." : "Reescrever Serviços com IA"}
              onClick={() => onOpenAiDialog("services", "Serviços")}
              className="gap-1 text-xs border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
            >
              <Sparkles className="size-3.5 text-purple-400" />
              Reescrever Serviços com IA
            </Button>
          )}
          <Button size="sm" onClick={addService} variant="outline" className="gap-1.5">
            <Plus className="size-3.5" />
            Adicionar Serviço
          </Button>
        </div>
      </div>

      <div className="space-y-4">
        {draftSpec.services.map((service, index) => {
          const titleErr = errors[`services.${index}.title`]
          const priceErr = errors[`services.${index}.priceFrom`]

          return (
            <div
              key={service.id || `srv-${index}`}
              className="rounded-lg border border-border bg-card p-4 space-y-3 relative"
            >
              <div className="flex items-center justify-between border-b pb-2">
                <span className="text-xs font-semibold text-muted-foreground">
                  Serviço #{index + 1}
                </span>

                <div className="flex items-center gap-1">
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="size-7"
                    disabled={index === 0}
                    onClick={() => moveService(index, "up")}
                    title="Subir"
                  >
                    <ArrowUp className="size-3.5" />
                  </Button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="size-7"
                    disabled={index === draftSpec.services.length - 1}
                    onClick={() => moveService(index, "down")}
                    title="Descer"
                  >
                    <ArrowDown className="size-3.5" />
                  </Button>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="size-7 text-destructive hover:text-destructive"
                    onClick={() => removeService(index)}
                    title="Remover serviço"
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Nome do Serviço *
                  </label>
                  <Input
                    value={service.title || ""}
                    onChange={(e) => updateService(index, { title: e.target.value })}
                    placeholder="Ex: Harmonização Facial"
                    className={titleErr ? "border-destructive" : ""}
                  />
                  {titleErr && <p className="text-xs text-destructive">{titleErr}</p>}
                </div>

                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Descrição Curta
                  </label>
                  <Input
                    value={service.shortDescription || ""}
                    onChange={(e) =>
                      updateService(index, { shortDescription: e.target.value })
                    }
                    placeholder="Ex: Procedimento estético para simetria facial"
                  />
                </div>

                <div className="space-y-1.5 sm:col-span-2">
                  <label className="text-xs font-medium text-muted-foreground">
                    Descrição Completa
                  </label>
                  <Textarea
                    value={service.description || ""}
                    onChange={(e) =>
                      updateService(index, { description: e.target.value })
                    }
                    placeholder="Detalhes completos sobre o procedimento, benefícios e cuidados"
                    rows={2}
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">
                    Preço Inicial (R$)
                  </label>
                  <Input
                    type="number"
                    min={0}
                    value={service.priceFrom ?? 0}
                    onChange={(e) =>
                      updateService(index, { priceFrom: Number(e.target.value) || 0 })
                    }
                    className={priceErr ? "border-destructive" : ""}
                  />
                  {priceErr && <p className="text-xs text-destructive">{priceErr}</p>}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">
                    Duração Estimada
                  </label>
                  <Input
                    value={service.duration || ""}
                    onChange={(e) => updateService(index, { duration: e.target.value })}
                    placeholder="Ex: 60 min"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">
                    Selo de Destaque (Opcional)
                  </label>
                  <Input
                    value={service.highlight || ""}
                    onChange={(e) => updateService(index, { highlight: e.target.value })}
                    placeholder="Ex: Mais Procurado"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-muted-foreground">
                    URL da Imagem
                  </label>
                  <Input
                    value={service.imageUrl || ""}
                    onChange={(e) => updateService(index, { imageUrl: e.target.value })}
                    placeholder="https://..."
                  />
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
