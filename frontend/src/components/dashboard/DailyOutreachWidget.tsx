import { Link } from "react-router-dom";
import { AlertTriangle, Zap, Sparkles, ArrowRight, Send } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { obterCockpitDiario } from "@/services/outreach";

export function DailyOutreachWidget() {
  const { data } = useQuery({
    queryKey: ["outreach", "daily-cockpit", "widget"],
    queryFn: () => obterCockpitDiario({ page_size: 1 }),
    staleTime: 10000,
  });

  const counts = data?.counts || { overdue: 0, ready_today: 0, new_contacts: 0 };

  return (
    <div className="rounded-2xl border border-primary/30 bg-card p-5 shadow-xs transition-all space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <Send className="size-4" />
          </div>
          <div>
            <h3 className="font-bold text-foreground text-sm">Prospecção de hoje</h3>
            <p className="text-xs text-muted-foreground">Visão geral das suas ações prioritárias do dia</p>
          </div>
        </div>

        <Link to="/outreach/hoje">
          <Button size="sm" className="h-8 text-xs gap-1">
            <span>Ver ações do dia</span>
            <ArrowRight className="size-3.5" />
          </Button>
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-3 pt-1">
        <div className="flex flex-col rounded-xl border border-destructive/20 bg-destructive/5 p-3">
          <div className="flex items-center gap-1.5 text-xs text-destructive font-medium">
            <AlertTriangle className="size-3.5" />
            <span>Atrasados</span>
          </div>
          <span className="mt-1 text-xl font-bold text-foreground">{counts.overdue}</span>
        </div>

        <div className="flex flex-col rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-3">
          <div className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium">
            <Zap className="size-3.5" />
            <span>Prontos hoje</span>
          </div>
          <span className="mt-1 text-xl font-bold text-foreground">{counts.ready_today}</span>
        </div>

        <div className="flex flex-col rounded-xl border border-sky-500/20 bg-sky-500/5 p-3">
          <div className="flex items-center gap-1.5 text-xs text-sky-600 dark:text-sky-400 font-medium">
            <Sparkles className="size-3.5" />
            <span>Novos contatos</span>
          </div>
          <span className="mt-1 text-xl font-bold text-foreground">{counts.new_contacts}</span>
        </div>
      </div>
    </div>
  );
}
