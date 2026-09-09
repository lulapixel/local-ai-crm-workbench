import { useState } from "react";
import { Copy, Check } from "lucide-react";
import { toast } from "sonner";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { saudacaoAtual } from "@/lib/saudacao";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { QueueItem } from "./types";

interface CopyMessageModalProps {
  item: QueueItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function CopyMessageModal({ item, open, onOpenChange }: CopyMessageModalProps) {
  const [msgKey, setMsgKey] = useState<string>("initial");
  const [incluirSaudacao, setIncluirSaudacao] = useState<boolean>(true);
  const [copiado, setCopiado] = useState(false);

  if (!item || !item.conversion_pack) return null;

  const pack = item.conversion_pack;
  const initialMsg = pack.initial_message || "";

  // Obtém o texto baseado na chave selecionada
  let textoBase = initialMsg;

  if (msgKey === "prototypeDelivery") {
    const protoUrl = item.landing_page?.public_url || item.landing_page?.preview_url || "";
    textoBase = `Oi, conforme conversamos, montei uma prévia de como pode ficar a presença digital da ${item.lead.name}: ${protoUrl}`;
  } else if (msgKey === "followup1") {
    textoBase = `Oi! Conseguiram dar uma olhada na mensagem anterior? Fiquei à disposição pra tirarmos dúvidas.`;
  } else if (msgKey === "followup2") {
    textoBase = `Olá, tudo bem? Sei que a rotina é corrida. Se fizer sentido, posso mostrar em 5 minutos como aumentar os agendamentos da ${item.lead.name}.`;
  } else if (msgKey === "closing") {
    textoBase = `Entendido! Vou encerrar os contatos por aqui pra não incomodar. Se em algum momento precisarem melhorar a captação de clientes da ${item.lead.name}, estamos à disposição!`;
  }

  const saudacao = saudacaoAtual();
  const textoFinal = incluirSaudacao
    ? `${saudacao}! ${textoBase.replace(/^(Oi|Olá|Bom dia|Boa tarde|Boa noite)[!.,]?\s*/i, "")}`
    : textoBase;

  const handleCopy = () => {
    navigator.clipboard.writeText(textoFinal);
    setCopiado(true);
    toast.success("Mensagem copiada para a área de transferência!");
    setTimeout(() => setCopiado(false), 2000);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Copy className="size-5 text-primary" />
            Copiar mensagem de abordagem
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="flex items-center justify-between gap-3">
            <div className="space-y-1 flex-1">
              <Label htmlFor="msg-select">Etapa da mensagem</Label>
              <Select value={msgKey} onValueChange={setMsgKey}>
                <SelectTrigger id="msg-select">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="initial">Mensagem inicial</SelectItem>
                  <SelectItem value="prototypeDelivery">Entrega do protótipo</SelectItem>
                  <SelectItem value="followup1">Follow-up 1 (+3 dias)</SelectItem>
                  <SelectItem value="followup2">Follow-up 2 (+5 dias)</SelectItem>
                  <SelectItem value="closing">Encerramento de cadência</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="saudacao-check"
                checked={incluirSaudacao}
                onChange={(e) => setIncluirSaudacao(e.target.checked)}
                className="size-4 rounded border-input"
              />
              <Label htmlFor="saudacao-check" className="text-xs font-normal cursor-pointer">
                Ajustar saudação ({saudacao})
              </Label>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs text-muted-foreground">Pré-visualização do texto</Label>
            <Textarea
              value={textoFinal}
              readOnly
              rows={5}
              className="resize-none font-mono text-xs bg-muted/30"
            />
          </div>
        </div>

        <div className="flex items-center justify-between border-t pt-3">
          <span className="text-xs text-muted-foreground">
            Empresa: <strong>{item.lead.name}</strong>
          </span>
          <Button onClick={handleCopy} className="gap-1.5">
            {copiado ? <Check className="size-4" /> : <Copy className="size-4" />}
            {copiado ? "Copiado!" : "Copiar mensagem"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
