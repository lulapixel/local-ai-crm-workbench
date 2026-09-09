import type { LandingPageData } from "@/features/landing-pages/types"
import type { EditorValidationErrors } from "../editor-types"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Button } from "@/components/ui/button"
import { Sparkles } from "lucide-react"

interface ContentFieldsProps {
  draftSpec: LandingPageData
  updateContentField: (field: string, value: string) => void
  errors: EditorValidationErrors
  isDirty?: boolean
  onOpenAiDialog?: (sectionKey: string, sectionLabel: string) => void
}

export function ContentFields({
  draftSpec,
  updateContentField,
  errors,
  isDirty,
  onOpenAiDialog,
}: ContentFieldsProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div className="flex items-center justify-between border-b pb-2">
          <h3 className="text-sm font-semibold text-foreground">
            Seção Hero (Principal)
          </h3>
          {onOpenAiDialog && (
            <Button
              size="sm"
              variant="outline"
              disabled={isDirty}
              title={isDirty ? "Salve ou descarte suas alterações antes de usar a IA." : "Reescrever Hero com IA"}
              onClick={() => onOpenAiDialog("hero", "Hero")}
              className="gap-1.5 text-xs border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
            >
              <Sparkles className="size-3.5 text-purple-400" />
              Reescrever Hero com IA
            </Button>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Selo / Badge do Hero
          </label>
          <Input
            value={draftSpec.hero.badge || ""}
            onChange={(e) => updateContentField("hero.badge", e.target.value)}
            placeholder="Ex: ★ Atendimento de Excelência"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Título Principal *
          </label>
          <Input
            value={draftSpec.hero.title || ""}
            onChange={(e) => updateContentField("hero.title", e.target.value)}
            placeholder="Ex: Realce sua beleza natural com tratamentos exclusivos"
            className={errors["hero.title"] ? "border-destructive" : ""}
          />
          {errors["hero.title"] && (
            <p className="text-xs text-destructive">{errors["hero.title"]}</p>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Texto Destacado no Título
          </label>
          <Input
            value={draftSpec.hero.highlightedText || ""}
            onChange={(e) => updateContentField("hero.highlightedText", e.target.value)}
            placeholder="Ex: beleza natural"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Descrição do Hero
          </label>
          <Textarea
            value={draftSpec.hero.description || ""}
            onChange={(e) => updateContentField("hero.description", e.target.value)}
            placeholder="Descrição curta que engaja o visitante no topo da página"
            rows={3}
          />
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Botão CTA Principal
            </label>
            <Input
              value={draftSpec.hero.primaryCta || ""}
              onChange={(e) => updateContentField("hero.primaryCta", e.target.value)}
              placeholder="Ex: Agendar Consulta"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              Botão CTA Secundário
            </label>
            <Input
              value={draftSpec.hero.secondaryCta || ""}
              onChange={(e) => updateContentField("hero.secondaryCta", e.target.value)}
              placeholder="Ex: Ver Tratamentos"
            />
          </div>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Selo de Disponibilidade
          </label>
          <Input
            value={draftSpec.hero.availabilityLabel || ""}
            onChange={(e) => updateContentField("hero.availabilityLabel", e.target.value)}
            placeholder="Ex: Próximas vagas disponíveis esta semana"
          />
        </div>
      </div>

      <div className="space-y-4 pt-4 border-t">
        <div className="flex items-center justify-between border-b pb-2">
          <h3 className="text-sm font-semibold text-foreground">
            Chamada Final (CTA de Encerramento)
          </h3>
          {onOpenAiDialog && (
            <Button
              size="sm"
              variant="outline"
              disabled={isDirty}
              title={isDirty ? "Salve ou descarte suas alterações antes de usar a IA." : "Reescrever CTA com IA"}
              onClick={() => onOpenAiDialog("finalCta", "Chamada Final (CTA)")}
              className="gap-1.5 text-xs border-purple-500/30 text-purple-300 hover:bg-purple-500/10"
            >
              <Sparkles className="size-3.5 text-purple-400" />
              Reescrever CTA com IA
            </Button>
          )}
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Título Final
          </label>
          <Input
            value={draftSpec.finalCta.title || ""}
            onChange={(e) => updateContentField("finalCta.title", e.target.value)}
            placeholder="Ex: Pronto para transformar seu visual?"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Descrição Final
          </label>
          <Textarea
            value={draftSpec.finalCta.description || ""}
            onChange={(e) => updateContentField("finalCta.description", e.target.value)}
            placeholder="Mensagem final convidando o prospect para o WhatsApp"
            rows={3}
          />
        </div>
      </div>
    </div>
  )
}
