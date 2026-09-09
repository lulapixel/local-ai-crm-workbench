import { Calendar, RefreshCw, Send, Play } from "lucide-react";
import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";

interface DailyOutreachHeaderProps {
  onRefresh: () => void;
  onStartSession: () => void;
  isRefreshing?: boolean;
}

export function DailyOutreachHeader({ onRefresh, onStartSession, isRefreshing }: DailyOutreachHeaderProps) {
  const dataFormatada = new Date().toLocaleDateString("pt-BR", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });

  const dataCapitalizada = dataFormatada.charAt(0).toUpperCase() + dataFormatada.slice(1);

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b pb-4">
      <div>
        <div className="flex items-center gap-2 text-xs font-semibold text-primary uppercase tracking-wider">
          <Calendar className="size-3.5" />
          <span>{dataCapitalizada}</span>
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
          Prospecção do dia
        </h1>
        <p className="text-xs text-muted-foreground mt-0.5">
          Suas ações comerciais prioritárias organizadas e prontas para execução.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={isRefreshing} className="h-9 text-xs gap-1.5">
          <RefreshCw className={`size-3.5 ${isRefreshing ? "animate-spin" : ""}`} />
          <span>Atualizar</span>
        </Button>

        <Link to="/abordagens">
          <Button variant="outline" size="sm" className="h-9 text-xs gap-1.5">
            <Send className="size-3.5" />
            <span>Central de Abordagens</span>
          </Button>
        </Link>

        <Button size="sm" onClick={onStartSession} className="h-9 text-xs gap-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-medium">
          <Play className="size-3.5 fill-white" />
          <span>Iniciar sessão</span>
        </Button>
      </div>
    </div>
  );
}
