import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Flame,
  Globe,
  MessageSquare,
  RefreshCw,
  Sparkles,
  Target,
} from "lucide-react";
import type { Lead } from "@/types/lead";
import type { ConversionPack } from "@/types/outreach";
import { obterPacoteConversao, gerarPacoteConversao } from "@/services/outreach";
import { ConversionPackModal } from "@/components/lead-detail/ConversionPackModal";

interface ConversionPackCardProps {
  lead: Lead;
}

export function ConversionPackCard({ lead }: ConversionPackCardProps) {
  const [pack, setPack] = useState<ConversionPack | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setIsLoading(true);
    setError(null);
    obterPacoteConversao(lead.place_id)
      .then((p) => {
        if (isMounted) setPack(p);
      })
      .catch((err) => {
        if (isMounted) console.error("Erro ao carregar pacote:", err);
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, [lead.place_id]);

  const handleGerarOuObter = async (force: boolean = false) => {
    setIsLoading(true);
    setError(null);
    try {
      const novoPacote = await gerarPacoteConversao(lead.place_id, { forceRegenerate: force });
      setPack(novoPacote);
      setIsModalOpen(true);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Erro ao gerar pacote de conversão";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      <div className="space-y-3.5 rounded-xl border border-primary/30 bg-primary/[0.03] p-4 font-sans shadow-sm">
        <div className="flex items-center justify-between gap-2">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <Target className="size-4 text-primary" />
            Pacote de Conversão
          </h3>

          {pack ? (
            <Badge
              variant="outline"
              className={
                pack.status === "approved"
                  ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-500"
                  : pack.status === "archived"
                  ? "border-muted bg-muted text-muted-foreground"
                  : "border-amber-500/40 bg-amber-500/10 text-amber-500"
              }
            >
              {pack.status === "approved"
                ? "Aprovado"
                : pack.status === "archived"
                ? "Arquivado"
                : "Rascunho v" + pack.version}
            </Badge>
          ) : (
            <Badge variant="outline" className="border-primary/30 text-primary">
              Pronto para Gerar
            </Badge>
          )}
        </div>

        {pack ? (
          <>
            <div className="space-y-1">
              <span className="flex items-center gap-1 text-xs font-bold uppercase tracking-wider text-primary">
                <Flame className="size-3.5" />
                Oportunidade Comercial
              </span>
              <p className="text-sm font-medium leading-snug">{pack.strategy.opportunity}</p>
            </div>

            <div className="rounded-lg border border-border/80 bg-card p-3 space-y-1">
              <span className="text-xs font-semibold text-muted-foreground uppercase">Ângulo da Abordagem</span>
              <p className="text-xs leading-relaxed text-foreground">{pack.strategy.commercialAngle}</p>
            </div>

            <div className="flex flex-wrap items-center gap-2 pt-1">
              <Button
                size="sm"
                onClick={() => setIsModalOpen(true)}
                className="gap-1.5 text-xs font-medium"
              >
                <MessageSquare className="size-3.5" />
                Ver Pacote Completo
              </Button>

              {pack.landingPageId && (
                <Button size="sm" variant="outline" asChild className="gap-1.5 text-xs">
                  <a href={`/editor/${pack.landingPageId}`} target="_blank" rel="noreferrer">
                    <Globe className="size-3.5 text-primary" />
                    Abrir Protótipo #{pack.landingPageId}
                  </a>
                </Button>
              )}

              <Button
                size="sm"
                variant="ghost"
                onClick={() => handleGerarOuObter(true)}
                disabled={isLoading}
                title="Regenerar estratégia e mensagens via IA"
                className="gap-1 text-xs text-muted-foreground hover:text-foreground"
              >
                <RefreshCw className={`size-3 ${isLoading ? "animate-spin" : ""}`} />
                Regenerar
              </Button>
            </div>
          </>
        ) : (
          <div className="space-y-3">
            <p className="text-xs leading-relaxed text-muted-foreground">
              Gere um pacote completo contendo diagnóstico, ângulo comercial, sequência de mensagens (com follow-ups), quebra de objeções e orientação alinhada para o protótipo.
            </p>
            {error && <p className="text-xs text-destructive">{error}</p>}
            <Button
              size="sm"
              onClick={() => handleGerarOuObter(false)}
              disabled={isLoading}
              className="gap-1.5 text-xs bg-primary hover:bg-primary/90"
            >
              <Sparkles className={`size-3.5 ${isLoading ? "animate-spin" : ""}`} />
              {isLoading ? "Gerando Pacote..." : "Gerar Pacote de Conversão"}
            </Button>
          </div>
        )}
      </div>

      {pack && (
        <ConversionPackModal
          pack={pack}
          lead={lead}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onPackUpdated={(updated) => setPack(updated)}
        />
      )}
    </>
  );
}
