import { useState } from "react"
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query"
import {
  MessageSquare,
  PhoneCall,
  StickyNote,
  Bot,
  Copy,
  ExternalLink,
  Check,
  Plus,
  Sparkles,
  ArrowUpRight,
  ArrowDownLeft,
  Clock,
  Trash2,
} from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { toast } from "sonner"
import {
  obterConversaLead,
  registrarRespostaLead,
  registrarNotaLead,
  registrarLigacaoLead,
  sugerirRespostaIA,
  excluirInteracao,
} from "@/services/outreach"
import {
  CLASSIFICACOES_LABELS,
  type OutreachConversation,
  type ResponseClassification,
} from "@/types/outreach"
import type { Lead } from "@/types/lead"
import { safeWhatsAppUrl } from "@/lib/safeExternalUrl"

interface ContactHistorySectionProps {
  lead: Lead
}

export function ContactHistorySection({ lead }: ContactHistorySectionProps) {
  const queryClient = useQueryClient()
  const [modalRespostaAberta, setModalRespostaAberta] = useState(false)
  const [modalNotaAberta, setModalNotaAberta] = useState(false)
  const [modalLigacaoAberta, setModalLigacaoAberta] = useState(false)
  const [sugestaoIa, setSugestaoIa] = useState<string | null>(null)
  const [copiado, setCopiado] = useState(false)

  // Formulário de resposta
  const [classificacao, setClassificacao] = useState<ResponseClassification>("interested")
  const [conteudoResposta, setConteudoResposta] = useState("")
  const [notaOpcional, setNotaOpcional] = useState("")
  const [canal] = useState("whatsapp")

  // Formulário de nota
  const [conteudoNota, setConteudoNota] = useState("")

  // Formulário de ligação
  const [resumoLigacao, setResumoLigacao] = useState("")

  // Query da conversa
  const { data: conversa, isLoading } = useQuery<OutreachConversation>({
    queryKey: ["outreach-conversation", lead.place_id],
    queryFn: () => obterConversaLead(lead.place_id),
  })

  // Mutação registrar resposta
  const mutacaoResposta = useMutation({
    mutationFn: () =>
      registrarRespostaLead(lead.place_id, {
        classification: classificacao,
        content: conteudoResposta,
        channel: canal,
        note: notaOpcional,
      }),
    onSuccess: () => {
      toast.success("Resposta registrada com sucesso!")
      setModalRespostaAberta(false)
      setConteudoResposta("")
      setNotaOpcional("")
      queryClient.invalidateQueries({ queryKey: ["outreach-conversation", lead.place_id] })
      queryClient.invalidateQueries({ queryKey: ["outreach-daily-cockpit"] })
    },
    onError: (err: any) => {
      toast.error(err.message || "Erro ao registrar resposta")
    },
  })

  // Mutação registrar nota
  const mutacaoNota = useMutation({
    mutationFn: () => registrarNotaLead(lead.place_id, conteudoNota),
    onSuccess: () => {
      toast.success("Nota interna adicionada!")
      setModalNotaAberta(false)
      setConteudoNota("")
      queryClient.invalidateQueries({ queryKey: ["outreach-conversation", lead.place_id] })
    },
    onError: (err: any) => {
      toast.error(err.message || "Erro ao registrar nota")
    },
  })

  // Mutação registrar ligação
  const mutacaoLigacao = useMutation({
    mutationFn: () => registrarLigacaoLead(lead.place_id, { content: resumoLigacao }),
    onSuccess: () => {
      toast.success("Ligação registrada!")
      setModalLigacaoAberta(false)
      setResumoLigacao("")
      queryClient.invalidateQueries({ queryKey: ["outreach-conversation", lead.place_id] })
    },
    onError: (err: any) => {
      toast.error(err.message || "Erro ao registrar ligação")
    },
  })

  // Mutação IA sugestão
  const mutacaoSugestaoIa = useMutation({
    mutationFn: (interactionId: number) => sugerirRespostaIA(interactionId),
    onSuccess: (data) => {
      setSugestaoIa(data.suggested_reply)
      toast.success("Sugestão de resposta gerada por IA!")
    },
    onError: (err: any) => {
      toast.error(err.message || "Erro ao gerar sugestão por IA")
    },
  })

  // Mutação excluir interação
  const mutacaoExcluir = useMutation({
    mutationFn: (interactionId: number) => excluirInteracao(interactionId),
    onSuccess: () => {
      toast.success("Registro excluído!")
      queryClient.invalidateQueries({ queryKey: ["outreach-conversation", lead.place_id] })
    },
    onError: (err: any) => {
      toast.error(err.message || "Não é possível excluir esta mensagem.")
    },
  })

  const interacoes = conversa?.interactions || []
  const ultimaRespostaInbound = [...interacoes]
    .reverse()
    .find((i) => i.direction === "inbound" && i.interaction_type === "response")

  const copiarParaTransferencia = (texto: string) => {
    navigator.clipboard.writeText(texto)
    setCopiado(true)
    toast.success("Texto copiado!")
    setTimeout(() => setCopiado(false), 2000)
  }

  const formatarDataHora = (isoStr: string) => {
    try {
      const d = new Date(isoStr)
      return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" }) +
        " · " +
        d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })
    } catch {
      return isoStr
    }
  }

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card p-4 shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border pb-3">
        <div className="flex items-center gap-2">
          <MessageSquare className="size-4 text-primary" />
          <h3 className="font-semibold text-foreground text-sm">Histórico de contato</h3>
          {conversa?.status && (
            <Badge variant="outline" className="text-xs capitalize">
              {conversa.status.replace("_", " ")}
            </Badge>
          )}
        </div>

        {/* Botões de Ação */}
        <div className="flex flex-wrap items-center gap-1.5">
          <Button size="sm" variant="default" onClick={() => setModalRespostaAberta(true)} className="h-8 text-xs">
            <Plus className="size-3.5 mr-1" />
            Registrar resposta
          </Button>

          <Button size="sm" variant="outline" onClick={() => setModalNotaAberta(true)} className="h-8 text-xs">
            <StickyNote className="size-3.5 mr-1" />
            Nota
          </Button>

          <Button size="sm" variant="outline" onClick={() => setModalLigacaoAberta(true)} className="h-8 text-xs">
            <PhoneCall className="size-3.5 mr-1" />
            Ligação
          </Button>

          {safeWhatsAppUrl(lead.whatsapp_link) && (
            <Button
              size="sm"
              variant="secondary"
              asChild
              className="h-8 text-xs text-emerald-600 dark:text-emerald-400"
              title="Abre o WhatsApp diretamente (não altera o status da sequência nem registra envio automático)"
            >
              <a href={safeWhatsAppUrl(lead.whatsapp_link)} target="_blank" rel="noopener noreferrer">
                <ExternalLink className="size-3.5 mr-1" />
                WhatsApp
              </a>
            </Button>
          )}
        </div>
      </div>

      {/* Próxima Ação Sugerida */}
      {conversa?.next_action_note && (
        <div className="flex items-center justify-between rounded-lg bg-primary/10 px-3 py-2 text-xs font-medium text-primary border border-primary/20">
          <div className="flex items-center gap-2">
            <Clock className="size-4 text-primary shrink-0" />
            <span>
              <strong>Próxima ação:</strong> {conversa.next_action_note}
            </span>
          </div>
          {ultimaRespostaInbound && (
            <Button
              size="sm"
              variant="ghost"
              className="h-7 text-xs hover:bg-primary/20"
              onClick={() => mutacaoSugestaoIa.mutate(ultimaRespostaInbound.id)}
              disabled={mutacaoSugestaoIa.isPending}
            >
              <Sparkles className="size-3 mr-1 text-amber-500 animate-pulse" />
              {mutacaoSugestaoIa.isPending ? "Gerando..." : "Sugerir resposta"}
            </Button>
          )}
        </div>
      )}

      {/* Caixa de Sugestão de Resposta por IA */}
      {sugestaoIa && (
        <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 space-y-2 text-xs">
          <div className="flex items-center justify-between text-amber-600 dark:text-amber-400 font-medium">
            <span className="flex items-center gap-1">
              <Bot className="size-4" />
              Sugestão de Resposta (IA assistida)
            </span>
            <Button
              size="sm"
              variant="outline"
              className="h-6 text-[10px] border-amber-500/30"
              onClick={() => copiarParaTransferencia(sugestaoIa)}
            >
              {copiado ? <Check className="size-3 text-emerald-500" /> : <Copy className="size-3 mr-1" />}
              Copiar
            </Button>
          </div>
          <Textarea
            value={sugestaoIa}
            onChange={(e) => setSugestaoIa(e.target.value)}
            className="bg-background text-xs min-h-[60px]"
          />
          <p className="text-[10px] text-muted-foreground">
            Você pode editar a mensagem acima antes de copiar. Nenhuma sugestão é enviada automaticamente.
          </p>
        </div>
      )}

      {/* Timeline de Interações */}
      {isLoading ? (
        <div className="py-6 text-center text-xs text-muted-foreground">Carregando histórico de contato...</div>
      ) : interacoes.length === 0 ? (
        <div className="rounded-lg border border-dashed border-border p-6 text-center text-xs text-muted-foreground space-y-1">
          <p className="font-medium text-foreground">Nenhum contato registrado ainda</p>
          <p>As mensagens enviadas na régua operacional e as respostas do lead aparecerão aqui.</p>
        </div>
      ) : (
        <div className="relative space-y-3 pl-4 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
          {interacoes.map((item) => {
            const isOutbound = item.direction === "outbound"
            const isInbound = item.direction === "inbound"

            return (
              <div key={item.id} className="relative group text-xs">
                {/* Indicador visual de timeline */}
                <div
                  className={`absolute -left-[21px] top-1 flex size-3.5 items-center justify-center rounded-full text-[10px] ${
                    isOutbound
                      ? "bg-primary text-primary-foreground"
                      : isInbound
                      ? "bg-emerald-500 text-white"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {isOutbound ? (
                    <ArrowUpRight className="size-2.5" />
                  ) : isInbound ? (
                    <ArrowDownLeft className="size-2.5" />
                  ) : (
                    <StickyNote className="size-2.5" />
                  )}
                </div>

                <div className="rounded-lg border border-border bg-background p-3 space-y-1.5">
                  <div className="flex items-center justify-between text-muted-foreground text-[11px]">
                    <div className="flex items-center gap-1.5 font-medium text-foreground">
                      <span>
                        {isOutbound
                          ? "Você enviou"
                          : isInbound
                          ? "Lead respondeu"
                          : "Observação interna"}
                      </span>
                      <span className="text-muted-foreground font-normal">
                        ({item.channel})
                      </span>
                    </div>

                    <div className="flex items-center gap-2">
                      <span>{formatarDataHora(item.occurred_at)}</span>

                      {!isOutbound && (
                        <button
                          type="button"
                          onClick={() => mutacaoExcluir.mutate(item.id)}
                          className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-opacity"
                          title="Excluir este registro"
                        >
                          <Trash2 className="size-3" />
                        </button>
                      )}
                    </div>
                  </div>

                  {item.content && (
                    <p className="text-foreground whitespace-pre-wrap leading-relaxed">
                      “{item.content}”
                    </p>
                  )}

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    {item.classification && (
                      <Badge variant="secondary" className="text-[10px]">
                        Classificação:{" "}
                        {CLASSIFICACOES_LABELS[item.classification as ResponseClassification] ||
                          item.classification}
                      </Badge>
                    )}

                    {isInbound && item.id === ultimaRespostaInbound?.id && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-5 px-1.5 text-[10px] text-amber-600 dark:text-amber-400 hover:bg-amber-500/10"
                        onClick={() => mutacaoSugestaoIa.mutate(item.id)}
                        disabled={mutacaoSugestaoIa.isPending}
                      >
                        <Sparkles className="size-2.5 mr-1" />
                        Sugerir resposta por IA
                      </Button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {/* Modal Registrar Resposta */}
      <Dialog open={modalRespostaAberta} onOpenChange={setModalRespostaAberta}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Registrar resposta recebida</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2 text-xs">
            <div>
              <label className="font-medium text-foreground block mb-1">
                Classificação comercial *
              </label>
              <Select
                value={classificacao}
                onValueChange={(val) => setClassificacao(val as ResponseClassification)}
              >
                <SelectTrigger className="text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {Object.entries(CLASSIFICACOES_LABELS).map(([chave, rotulo]) => (
                    <SelectItem key={chave} value={chave} className="text-xs">
                      {rotulo}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="font-medium text-foreground block mb-1">
                Mensagem recebida do prospect
              </label>
              <Textarea
                placeholder="Ex: Gostei da demonstração. Quanto custa?"
                value={conteudoResposta}
                onChange={(e) => setConteudoResposta(e.target.value)}
                className="text-xs min-h-[80px]"
              />
            </div>

            <div>
              <label className="font-medium text-foreground block mb-1">
                Observação interna opcional
              </label>
              <Input
                placeholder="Ex: Responsável pediu proposta amanhã"
                value={notaOpcional}
                onChange={(e) => setNotaOpcional(e.target.value)}
                className="text-xs"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              size="sm"
              variant="outline"
              onClick={() => setModalRespostaAberta(false)}
            >
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={() => mutacaoResposta.mutate()}
              disabled={mutacaoResposta.isPending}
            >
              {mutacaoResposta.isPending ? "Salvando..." : "Confirmar e interromper cadência"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Adicionar Nota */}
      <Dialog open={modalNotaAberta} onOpenChange={setModalNotaAberta}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Adicionar nota interna</DialogTitle>
          </DialogHeader>
          <div className="py-2 text-xs">
            <Textarea
              placeholder="Digite sua observação sobre o lead..."
              value={conteudoNota}
              onChange={(e) => setConteudoNota(e.target.value)}
              className="text-xs min-h-[100px]"
            />
          </div>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setModalNotaAberta(false)}>
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={() => mutacaoNota.mutate()}
              disabled={!conteudoNota.trim() || mutacaoNota.isPending}
            >
              Salvar nota
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Modal Registrar Ligação */}
      <Dialog open={modalLigacaoAberta} onOpenChange={setModalLigacaoAberta}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Registrar ligação telefônica</DialogTitle>
          </DialogHeader>
          <div className="py-2 text-xs">
            <Textarea
              placeholder="Resumo da conversa por telefone..."
              value={resumoLigacao}
              onChange={(e) => setResumoLigacao(e.target.value)}
              className="text-xs min-h-[100px]"
            />
          </div>
          <DialogFooter>
            <Button size="sm" variant="outline" onClick={() => setModalLigacaoAberta(false)}>
              Cancelar
            </Button>
            <Button
              size="sm"
              onClick={() => mutacaoLigacao.mutate()}
              disabled={mutacaoLigacao.isPending}
            >
              Salvar ligação
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
