import type { LandingPageData } from "@/features/landing-pages/types"
import type { EditorValidationErrors } from "../editor-types"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"

interface ContactFieldsProps {
  draftSpec: LandingPageData
  updateContactField: (field: keyof LandingPageData["contact"], value: string) => void
  errors: EditorValidationErrors
}

export function ContactFields({ draftSpec, updateContactField, errors }: ContactFieldsProps) {
  const whatsappErr = errors["contact.whatsappNumber"]

  return (
    <div className="space-y-6">
      <div className="space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-foreground border-b pb-2">
            Canais de Contato e Localização
          </h3>
          <p className="text-xs text-muted-foreground mt-1">
            Essas informações são usadas para gerar os botões de ação e dados do rodapé.
          </p>
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Número do WhatsApp (com DDD) *
          </label>
          <Input
            value={draftSpec.contact.whatsappNumber || ""}
            onChange={(e) => updateContactField("whatsappNumber", e.target.value)}
            placeholder="Ex: 5541999998888 ou (41) 99999-8888"
            className={whatsappErr ? "border-destructive" : ""}
          />
          <p className="text-[11px] text-muted-foreground">
            O número é formatado e normalizado automaticamente no salvamento.
          </p>
          {whatsappErr && <p className="text-xs text-destructive">{whatsappErr}</p>}
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Mensagem Inicial do WhatsApp
          </label>
          <Textarea
            value={draftSpec.contact.whatsappMessage || ""}
            onChange={(e) => updateContactField("whatsappMessage", e.target.value)}
            placeholder="Ex: Olá! Gostaria de agendar uma avaliação."
            rows={2}
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Cidade e Estado
          </label>
          <Input
            value={draftSpec.contact.city || ""}
            onChange={(e) => updateContactField("city", e.target.value)}
            placeholder="Ex: Curitiba - PR"
          />
        </div>

        <div className="space-y-1.5">
          <label className="text-xs font-medium text-muted-foreground">
            Instagram (Usuário ou Link)
          </label>
          <Input
            value={draftSpec.contact.instagram || ""}
            onChange={(e) => updateContactField("instagram", e.target.value)}
            placeholder="Ex: @clinicaaureaestetica"
          />
        </div>
      </div>
    </div>
  )
}
