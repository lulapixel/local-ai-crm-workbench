import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  CheckCircle2,
  Copy,
  ExternalLink,
  Flame,
  Globe,
  Lightbulb,
  MessageSquare,
  RefreshCw,
  Save,
  ShieldAlert,
  Sparkles,
  Target,
} from "lucide-react";
import type { ConversionPack } from "@/types/outreach";
import type { Lead } from "@/types/lead";
import {
  aprovarPacoteConversao,
  arquivarPacoteConversao,
  atualizarPacoteConversao,
  regenerarSecoesPacote,
} from "@/services/outreach";

interface ConversionPackModalProps {
  pack: ConversionPack | null;
  lead: Lead;
  isOpen: boolean;
  onClose: () => void;
  onPackUpdated: (updated: ConversionPack) => void;
}

export function ConversionPackModal({
  pack,
  lead,
  isOpen,
  onClose,
  onPackUpdated,
}: ConversionPackModalProps) {
  const [activeTab, setActiveTab] = useState<"strategy" | "messages" | "objections" | "prototype">("strategy");
  const [editedPack, setEditedPack] = useState<ConversionPack | null>(pack);
  const [isSaving, setIsSaving] = useState(false);
  const [isRegenerating, setIsRegenerating] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [showRegenPrompt, setShowRegenPrompt] = useState(false);
  const [copiedKey, setCopiedKey] = useState<string | null>(null);

  useEffect(() => {
    setEditedPack(pack);
  }, [pack]);

  if (!editedPack) return null;

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 2000);
  };

  const handleSave = async () => {
    if (!editedPack) return;
    setIsSaving(true);
    try {
      const updated = await atualizarPacoteConversao(editedPack.id, {
        messages: editedPack.messages,
        objections: editedPack.objections,
        prototype: editedPack.prototype,
      });
      setEditedPack(updated);
      onPackUpdated(updated);
    } catch (e) {
      console.error("Erro ao salvar pacote:", e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleApprove = async () => {
    if (!editedPack) return;
    setIsSaving(true);
    try {
      const updated = await aprovarPacoteConversao(editedPack.id);
      setEditedPack(updated);
      onPackUpdated(updated);
    } catch (e) {
      console.error("Erro ao aprovar pacote:", e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleArchive = async () => {
    if (!editedPack) return;
    setIsSaving(true);
    try {
      const updated = await arquivarPacoteConversao(editedPack.id);
      setEditedPack(updated);
      onPackUpdated(updated);
    } catch (e) {
      console.error("Erro ao arquivar pacote:", e);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRegenerate = async (sections: string[]) => {
    if (!editedPack) return;
    setIsRegenerating(true);
    try {
      const updated = await regenerarSecoesPacote(editedPack.id, sections, instruction);
      setEditedPack(updated);
      onPackUpdated(updated);
      setShowRegenPrompt(false);
      setInstruction("");
    } catch (e) {
      console.error("Erro ao regenerar pacote:", e);
    } finally {
      setIsRegenerating(false);
    }
  };

  const updateMessageField = (field: keyof Omit<ConversionPack["messages"], "followups">, val: string) => {
    setEditedPack((prev) => prev ? ({
      ...prev,
      messages: {
        ...prev.messages,
        [field]: val,
      },
    }) : null);
  };

  const updateFollowupMessage = (index: number, val: string) => {
    setEditedPack((prev) => {
      if (!prev) return null;
      const newFollowups = [...prev.messages.followups];
      newFollowups[index] = { ...newFollowups[index], message: val };
      return {
        ...prev,
        messages: {
          ...prev.messages,
          followups: newFollowups,
        },
      };
    });
  };

  const updateObjectionResponse = (index: number, val: string) => {
    setEditedPack((prev) => {
      if (!prev) return null;
      const newObjs = [...prev.objections];
      newObjs[index] = { ...newObjs[index], response: val };
      return {
        ...prev,
        objections: newObjs,
      };
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-h-[92vh] max-w-4xl overflow-y-auto p-0 sm:max-w-5xl">
        <DialogHeader className="border-b border-border px-6 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <DialogTitle className="flex items-center gap-2 text-lg">
                Pacote de Conversão — {lead.nome}
              </DialogTitle>
              <p className="text-xs text-muted-foreground">
                Versão {editedPack.version} · Criado via {editedPack.provider || "IA/Fallback"} · ID #{editedPack.id}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant="outline"
                className={
                  editedPack.status === "approved"
                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-500"
                    : editedPack.status === "archived"
                    ? "border-muted bg-muted text-muted-foreground"
                    : "border-amber-500/40 bg-amber-500/10 text-amber-500"
                }
              >
                {editedPack.status === "approved"
                  ? "Aprovado"
                  : editedPack.status === "archived"
                  ? "Arquivado"
                  : "Rascunho"}
              </Badge>
              {editedPack.status !== "approved" && (
                <Button size="sm" onClick={handleApprove} disabled={isSaving} className="gap-1 bg-emerald-600 hover:bg-emerald-700">
                  <CheckCircle2 className="size-3.5" />
                  Aprovar Pacote
                </Button>
              )}
            </div>
          </div>

          {/* Abas */}
          <div className="flex gap-2 border-t border-border/60 pt-3 text-xs">
            <button
              onClick={() => setActiveTab("strategy")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
                activeTab === "strategy"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground"
              }`}
            >
              <Target className="size-3.5" />
              1. Estratégia Comercial
            </button>
            <button
              onClick={() => setActiveTab("messages")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
                activeTab === "messages"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground"
              }`}
            >
              <MessageSquare className="size-3.5" />
              2. Sequência de Mensagens
            </button>
            <button
              onClick={() => setActiveTab("objections")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
                activeTab === "objections"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground"
              }`}
            >
              <ShieldAlert className="size-3.5" />
              3. Quebra de Objeções
            </button>
            <button
              onClick={() => setActiveTab("prototype")}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 font-medium transition-colors ${
                activeTab === "prototype"
                  ? "bg-primary text-primary-foreground"
                  : "hover:bg-muted text-muted-foreground"
              }`}
            >
              <Globe className="size-3.5" />
              4. Orientação do Protótipo
            </button>
          </div>
        </DialogHeader>

        <div className="p-6">
          {/* TAB 1: ESTRATÉGIA */}
          {activeTab === "strategy" && (
            <div className="space-y-5">
              <div className="rounded-xl border border-primary/20 bg-primary/5 p-4">
                <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-primary">
                  <Flame className="size-4" />
                  Oportunidade Principal
                </h4>
                <p className="mt-1 text-sm font-medium">{editedPack.strategy.opportunity}</p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-border bg-card p-4">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">Problema Identificado</h4>
                  <p className="mt-1 text-sm leading-relaxed">{editedPack.strategy.problem}</p>
                </div>

                <div className="rounded-xl border border-border bg-card p-4">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">Ângulo de Abordagem</h4>
                  <p className="mt-1 text-sm leading-relaxed">{editedPack.strategy.commercialAngle}</p>
                </div>
              </div>

              <div className="rounded-xl border border-border bg-card p-4">
                <h4 className="flex items-center gap-1.5 text-xs font-semibold uppercase text-muted-foreground">
                  <Lightbulb className="size-3.5" />
                  Evidências Reais Extraídas
                </h4>
                <ul className="mt-2 space-y-1.5">
                  {editedPack.strategy.evidence.map((ev, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                      <span className="mt-1.5 size-1.5 shrink-0 rounded-full bg-primary" />
                      <span>{ev}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rounded-xl border border-border bg-card p-4">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">CTA Recomendado</h4>
                <p className="mt-1 text-sm font-medium text-foreground">{editedPack.strategy.recommendedCta}</p>
              </div>
            </div>
          )}

          {/* TAB 2: MENSAGENS */}
          {activeTab === "messages" && (
            <div className="space-y-6">
              {/* Mensagem Inicial */}
              <div className="space-y-2 rounded-xl border border-border bg-card p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-primary">Dia 0 — Abordagem Inicial</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleCopy(editedPack.messages.initial, "initial")}
                    className="gap-1 text-xs"
                  >
                    <Copy className="size-3" />
                    {copiedKey === "initial" ? "Copiado!" : "Copiar"}
                  </Button>
                </div>
                <Textarea
                  value={editedPack.messages.initial}
                  onChange={(e) => updateMessageField("initial", e.target.value)}
                  className="min-h-[90px] text-sm"
                />
              </div>

              {/* Após Interesse */}
              <div className="space-y-2 rounded-xl border border-border bg-card p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-muted-foreground">Resposta ao Interesse do Lead</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleCopy(editedPack.messages.afterInterest, "afterInterest")}
                    className="gap-1 text-xs"
                  >
                    <Copy className="size-3" />
                    {copiedKey === "afterInterest" ? "Copiado!" : "Copiar"}
                  </Button>
                </div>
                <Textarea
                  value={editedPack.messages.afterInterest}
                  onChange={(e) => updateMessageField("afterInterest", e.target.value)}
                  className="min-h-[70px] text-sm"
                />
              </div>

              {/* Entrega do Protótipo */}
              <div className="space-y-2 rounded-xl border border-border bg-card p-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold uppercase text-muted-foreground">Envio do Link do Protótipo</span>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => handleCopy(editedPack.messages.prototypeDelivery, "proto")}
                    className="gap-1 text-xs"
                  >
                    <Copy className="size-3" />
                    {copiedKey === "proto" ? "Copiado!" : "Copiar"}
                  </Button>
                </div>
                <Textarea
                  value={editedPack.messages.prototypeDelivery}
                  onChange={(e) => updateMessageField("prototypeDelivery", e.target.value)}
                  className="min-h-[70px] text-sm"
                />
              </div>

              {/* Followups */}
              <div className="space-y-4 pt-2">
                <h4 className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Cadência de Follow-ups Programados
                </h4>
                {editedPack.messages.followups.map((f, idx) => (
                  <div key={idx} className="space-y-2 rounded-xl border border-border bg-card/60 p-4">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-foreground">
                        Follow-up #{f.order} (Dia +{f.delayDays}) — {f.objective}
                      </span>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleCopy(f.message, `f_${idx}`)}
                        className="gap-1 text-xs"
                      >
                        <Copy className="size-3" />
                        {copiedKey === `f_${idx}` ? "Copiado!" : "Copiar"}
                      </Button>
                    </div>
                    <Textarea
                      value={f.message}
                      onChange={(e) => updateFollowupMessage(idx, e.target.value)}
                      className="min-h-[70px] text-sm"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* TAB 3: OBJEÇÕES */}
          {activeTab === "objections" && (
            <div className="space-y-4">
              {editedPack.objections.map((item, idx) => (
                <div key={idx} className="space-y-2 rounded-xl border border-border bg-card p-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-500">Objeção: "{item.objection}"</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => handleCopy(item.response, `obj_${idx}`)}
                      className="gap-1 text-xs"
                    >
                      <Copy className="size-3" />
                      {copiedKey === `obj_${idx}` ? "Copiado!" : "Copiar Resposta"}
                    </Button>
                  </div>
                  <Textarea
                    value={item.response}
                    onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => updateObjectionResponse(idx, e.target.value)}
                    className="min-h-[70px] text-sm"
                  />
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: PROTÓTIPO */}
          {activeTab === "prototype" && (
            <div className="space-y-5">
              <div className="rounded-xl border border-border bg-card p-4">
                <h4 className="text-xs font-semibold uppercase text-muted-foreground">Título / Ângulo da Hero da LP</h4>
                <p className="mt-1 text-base font-bold text-foreground">{editedPack.prototype.heroAngle}</p>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-xl border border-border bg-card p-4">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">Foco de Conversão Visual</h4>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {editedPack.prototype.focus.map((f) => (
                      <Badge key={f} variant="secondary" className="text-xs">
                        {f}
                      </Badge>
                    ))}
                  </div>
                </div>

                <div className="rounded-xl border border-border bg-card p-4">
                  <h4 className="text-xs font-semibold uppercase text-muted-foreground">CTA Principal Recomendado</h4>
                  <p className="mt-1 text-sm font-semibold text-primary">{editedPack.prototype.primaryCta}</p>
                </div>
              </div>

              {editedPack.landingPageId && (
                <div className="flex items-center justify-between rounded-xl border border-primary/30 bg-primary/5 p-4">
                  <div>
                    <h4 className="text-sm font-semibold">Landing Page Vinculada #{editedPack.landingPageId}</h4>
                    <p className="text-xs text-muted-foreground">
                      O protótipo já recebeu as diretrizes comerciais de hero e CTA.
                    </p>
                  </div>
                  <Button size="sm" asChild className="gap-1.5">
                    <a href={`/editor/${editedPack.landingPageId}`} target="_blank" rel="noreferrer">
                      <ExternalLink className="size-3.5" />
                      Abrir Protótipo Visual
                    </a>
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Prompt de Regeneração */}
          {showRegenPrompt && (
            <div className="mt-6 rounded-xl border border-amber-500/30 bg-amber-500/5 p-4 space-y-3">
              <h4 className="flex items-center gap-1.5 text-xs font-bold uppercase text-amber-500">
                <Sparkles className="size-4" />
                Instrução para Regeneração por IA
              </h4>
              <Input
                placeholder="Ex: Use um tom mais direto e enfatize a agilidade de agendamento"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                className="text-sm"
              />
              <div className="flex justify-end gap-2 pt-1">
                <Button size="sm" variant="ghost" onClick={() => setShowRegenPrompt(false)}>
                  Cancelar
                </Button>
                <Button
                  size="sm"
                  onClick={() => handleRegenerate(["messages", "objections"])}
                  disabled={isRegenerating}
                  className="gap-1"
                >
                  <RefreshCw className={`size-3 ${isRegenerating ? "animate-spin" : ""}`} />
                  Regenerar com Instrução
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Rodapé do Modal */}
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-border px-6 py-4">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowRegenPrompt(!showRegenPrompt)}
              disabled={isRegenerating}
              className="gap-1.5 text-xs"
            >
              <Sparkles className="size-3.5" />
              Regenerar IA
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handleArchive}
              disabled={isSaving}
              className="text-xs text-muted-foreground hover:text-destructive"
            >
              Arquivar
            </Button>
          </div>

          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={onClose}>
              Fechar
            </Button>
            <Button size="sm" onClick={handleSave} disabled={isSaving} className="gap-1.5">
              <Save className="size-3.5" />
              {isSaving ? "Salvando..." : "Salvar Alterações"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
