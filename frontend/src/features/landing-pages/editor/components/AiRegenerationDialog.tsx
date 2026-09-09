import { useState } from "react"
import { Sparkles, Loader2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

export type AiTone = "direct" | "premium" | "welcoming" | "short" | "commercial"

interface AiRegenerationDialogProps {
  isOpen: boolean
  onClose: () => void
  sectionKey: string
  sectionLabel: string
  onRegenerate: (sections: string[], tone: AiTone, instruction: string) => Promise<boolean>
}

const toneOptions: Array<{ id: AiTone; label: string; description: string }> = [
  { id: "premium", label: "Mais premium", description: "Tom exclusivo e sofisticado" },
  { id: "direct", label: "Mais direto", description: "Objetivo e sem rodeios" },
  { id: "welcoming", label: "Mais acolhedor", description: "Empático e humanizado" },
  { id: "short", label: "Mais curto", description: "Conciso e dinâmico" },
  { id: "commercial", label: "Mais comercial", description: "Focado em conversão e vendas" },
]

export function AiRegenerationDialog({
  isOpen,
  onClose,
  sectionKey,
  sectionLabel,
  onRegenerate,
}: AiRegenerationDialogProps) {
  const [selectedTone, setSelectedTone] = useState<AiTone>("premium")
  const [instruction, setInstruction] = useState("")
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async () => {
    setIsLoading(true)
    try {
      const success = await onRegenerate([sectionKey], selectedTone, instruction)
      if (success) {
        setInstruction("")
        onClose()
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && !isLoading && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Sparkles className="size-4 text-primary" />
            Reescrever {sectionLabel} com IA
          </DialogTitle>
          <DialogDescription>
            A IA irá reescrever exclusivamente a seção <strong>{sectionLabel}</strong>, mantendo intactas todas as outras seções e edições da página.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          {/* Seleção do Tom */}
          <div className="space-y-2">
            <label className="text-xs font-semibold text-foreground">
              Modo de Escrita (Tom)
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {toneOptions.map((tone) => {
                const isSelected = selectedTone === tone.id
                return (
                  <button
                    key={tone.id}
                    type="button"
                    onClick={() => setSelectedTone(tone.id)}
                    className={`flex flex-col text-left p-2.5 rounded-lg border text-xs transition-all ${
                      isSelected
                        ? "border-primary bg-primary/10 font-medium text-foreground"
                        : "border-border bg-card text-muted-foreground hover:bg-muted/50"
                    }`}
                  >
                    <span className="font-semibold text-foreground">{tone.label}</span>
                    <span className="text-[11px] opacity-80">{tone.description}</span>
                  </button>
                )
              })}
            </div>
          </div>

          {/* Instrução adicional */}
          <div className="space-y-1.5">
            <div className="flex justify-between items-center">
              <label className="text-xs font-semibold text-foreground">
                Instrução Adicional (Opcional)
              </label>
              <span className="text-[11px] text-muted-foreground">
                {instruction.length}/300
              </span>
            </div>
            <Textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value.slice(0, 300))}
              placeholder="Ex: Enfatize o atendimento personalizado e descontos na primeira consulta..."
              rows={3}
              maxLength={300}
            />
          </div>
        </div>

        <DialogFooter className="gap-2 sm:gap-0">
          <Button variant="outline" onClick={onClose} disabled={isLoading}>
            Cancelar
          </Button>
          <Button onClick={handleSubmit} disabled={isLoading}>
            {isLoading ? (
              <Loader2 className="mr-2 size-4 animate-spin" />
            ) : (
              <Sparkles className="mr-2 size-4" />
            )}
            Gerar nova versão
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
