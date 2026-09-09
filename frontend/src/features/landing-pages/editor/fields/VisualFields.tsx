import type { LandingPageData } from "@/features/landing-pages/types"
import type { EditorValidationErrors } from "../editor-types"
import { Input } from "@/components/ui/input"

interface VisualFieldsProps {
  draftSpec: LandingPageData
  updatePaletteColor: (key: keyof LandingPageData["palette"], hexValue: string) => void
  updateDraft: (updater: (prev: LandingPageData) => LandingPageData) => void
  errors: EditorValidationErrors
}

export function VisualFields({
  draftSpec,
  updatePaletteColor,
  updateDraft,
  errors,
}: VisualFieldsProps) {
  const paletteKeys: Array<{ key: keyof LandingPageData["palette"]; label: string }> = [
    { key: "background", label: "Fundo Geral (Background)" },
    { key: "surface", label: "Superfície de Cards (Surface)" },
    { key: "accent", label: "Cor de Destaque / Botão (Accent)" },
    { key: "accentStrong", label: "Destaque Secundário (Accent Strong)" },
    { key: "text", label: "Cor do Texto (Text)" },
    { key: "muted", label: "Texto Suave (Muted)" },
  ]

  return (
    <div className="space-y-6">
      {/* Elementos de Imagem */}
      <div className="space-y-4">
        <h3 className="text-sm font-semibold text-foreground border-b pb-2">
          Imagens e Identidade Visual
        </h3>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Nome da Marca / Empresa
          </label>
          <Input
            value={draftSpec?.brand?.name || ""}
            onChange={(e) =>
              updateDraft((prev) => ({
                ...prev,
                brand: { ...(prev.brand || {}), name: e.target.value },
              }))
            }
            placeholder="Ex: Clínica Áurea Estética"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            URL do Logo (Opcional)
          </label>
          <Input
            value={draftSpec?.brand?.logoUrl || ""}
            onChange={(e) =>
              updateDraft((prev) => ({
                ...prev,
                brand: { ...(prev.brand || {}), logoUrl: e.target.value },
              }))
            }
            placeholder="https://..."
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            URL da Imagem Principal (Hero)
          </label>
          <Input
            value={draftSpec.hero.imageUrl || ""}
            onChange={(e) =>
              updateDraft((prev) => ({
                ...prev,
                hero: { ...prev.hero, imageUrl: e.target.value },
              }))
            }
            placeholder="https://..."
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Texto Alternativo da Imagem (Alt)
          </label>
          <Input
            value={draftSpec.hero.imageAlt || ""}
            onChange={(e) =>
              updateDraft((prev) => ({
                ...prev,
                hero: { ...prev.hero, imageAlt: e.target.value },
              }))
            }
            placeholder="Ex: Fotografia de atendimento estético em clínica"
          />
        </div>
      </div>

      {/* Paleta de Cores */}
      <div className="space-y-4 pt-4 border-t">
        <div>
          <h3 className="text-sm font-semibold text-foreground">
            Paleta de Cores do Tema
          </h3>
          <p className="text-xs text-muted-foreground">
            Selecione com o seletor visual de cor ou digite o código hexadecimal.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {paletteKeys.map(({ key, label }) => {
            const hexVal = draftSpec.palette[key] || "#000000"
            const colorErr = errors[`palette.${key}`]

            return (
              <div key={key} className="space-y-1.5 rounded-lg border p-2.5 bg-card">
                <label className="text-xs font-medium text-muted-foreground block">
                  {label}
                </label>

                <div className="flex items-center gap-2">
                  <input
                    type="color"
                    value={hexVal.startsWith("#") ? hexVal : "#000000"}
                    onChange={(e) => updatePaletteColor(key, e.target.value)}
                    className="size-8 cursor-pointer rounded border border-border bg-transparent p-0.5"
                  />
                  <Input
                    value={hexVal}
                    onChange={(e) => updatePaletteColor(key, e.target.value)}
                    placeholder="#000000"
                    className={`font-mono text-xs ${colorErr ? "border-destructive" : ""}`}
                  />
                </div>
                {colorErr && <p className="text-xs text-destructive">{colorErr}</p>}
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
