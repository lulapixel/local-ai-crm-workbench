import type { LandingPageData } from "@/features/landing-pages/types"
import type { EditorValidationErrors } from "../editor-types"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

interface SeoFieldsProps {
  draftSpec: LandingPageData
  updateSeoField: (field: keyof LandingPageData["seo"], value: string) => void
  updateDraft: (updater: (prev: LandingPageData) => LandingPageData) => void
  errors: EditorValidationErrors
}

export function SeoFields({ draftSpec, updateSeoField, updateDraft }: SeoFieldsProps) {
  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground border-b pb-2">
            Otimização para Buscadores (SEO)
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Configure o título e descrição exibidos no Google e ao compartilhar links em redes sociais.
          </p>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Título da Página (Meta Title)
          </label>
          <Input
            value={draftSpec.seo.title || ""}
            onChange={(e) => updateSeoField("title", e.target.value)}
            placeholder="Ex: Clínica Áurea Estética em Curitiba | Agende seu horário"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Descrição da Página (Meta Description)
          </label>
          <Textarea
            value={draftSpec.seo.description || ""}
            onChange={(e) => updateSeoField("description", e.target.value)}
            placeholder="Descrição com resumo dos serviços para aparecer no resultado da busca"
            rows={3}
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Subtítulo de Compartilhamento / Eyebrow
          </label>
          <Input
            value={draftSpec?.brand?.eyebrow || ""}
            onChange={(e) =>
              updateDraft((prev) => ({
                ...prev,
                brand: { ...(prev.brand || {}), eyebrow: e.target.value },
              }))
            }
            placeholder="Ex: Estética Avançada e Bem-Estar"
          />
        </div>
      </div>
    </div>
  )
}
