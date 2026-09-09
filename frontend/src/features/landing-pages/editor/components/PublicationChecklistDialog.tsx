import { useState } from "react"
import { AlertTriangle, Globe, Loader2, ShieldCheck } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"

interface PublicationChecklistDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onConfirmPublish: () => Promise<void> | void
  isPublishing?: boolean
  publicationConfigured?: boolean
}

const CHECKLIST_ITEMS = [
  { id: "phone", label: "Telefone de contato e WhatsApp revisados e corretos." },
  { id: "prices", label: "Preços e condições comerciais revisados." },
  { id: "images", label: "Imagens, artes e marcas autorizadas." },
  { id: "testimonials", label: "Depoimentos autorizados e sem conteúdo fictício apresentado como real." },
  { id: "promises", label: "Promessas, prazos de entrega e garantias revisados." },
  { id: "data", label: "Dados cadastrais e endereço da empresa confirmados." },
]

export function PublicationChecklistDialog({
  open,
  onOpenChange,
  onConfirmPublish,
  isPublishing = false,
  publicationConfigured = true,
}: PublicationChecklistDialogProps) {
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({})

  const allChecked = CHECKLIST_ITEMS.every((item) => checkedItems[item.id])

  const toggleCheck = (id: string) => {
    setCheckedItems((prev) => ({ ...prev, [id]: !prev[id] }))
  }

  const handleConfirm = async () => {
    await onConfirmPublish()
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-foreground">
            <ShieldCheck className="size-5 text-primary" />
            Checklist de Segurança para Publicação
          </DialogTitle>
          <DialogDescription className="text-xs text-muted-foreground">
            Confirme os itens de conformidade antes de disponibilizar esta Landing Page para o prospect.
          </DialogDescription>
        </DialogHeader>

        {!publicationConfigured && (
          <div className="rounded-md border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-300 space-y-1">
            <div className="flex items-center gap-1.5 font-medium">
              <AlertTriangle className="size-4 text-amber-400" />
              Publicação externa não configurada
            </div>
            <p>
              Nenhum domínio público externo foi configurado (LP_PUBLIC_BASE_URL). A página será publicada em modo preview interno local.
            </p>
          </div>
        )}

        <div className="space-y-2 py-2">
          {CHECKLIST_ITEMS.map((item) => (
            <label
              key={item.id}
              className="flex items-start gap-2.5 rounded-md border border-border/60 p-2.5 text-xs text-foreground cursor-pointer hover:bg-accent/40 transition-colors"
            >
              <input
                type="checkbox"
                checked={Boolean(checkedItems[item.id])}
                onChange={() => toggleCheck(item.id)}
                className="mt-0.5 rounded border-input text-primary focus:ring-primary"
              />
              <span>{item.label}</span>
            </label>
          ))}
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => onOpenChange(false)}
            disabled={isPublishing}
          >
            Cancelar
          </Button>
          <Button
            type="button"
            size="sm"
            disabled={!allChecked || isPublishing}
            onClick={handleConfirm}
          >
            {isPublishing ? (
              <Loader2 className="mr-1.5 size-3.5 animate-spin" />
            ) : (
              <Globe className="mr-1.5 size-3.5" />
            )}
            Confirmar e Publicar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
