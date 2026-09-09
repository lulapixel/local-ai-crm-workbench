import { Search, RotateCcw } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { QueueFiltersState } from "./types";

interface OutreachQueueFiltersProps {
  filters: QueueFiltersState;
  onFilterChange: (filters: Partial<QueueFiltersState>) => void;
  onResetFilters: () => void;
}

export function OutreachQueueFilters({
  filters,
  onFilterChange,
  onResetFilters,
}: OutreachQueueFiltersProps) {
  const hasActiveFilters =
    Boolean(filters.search) ||
    Boolean(filters.niche) ||
    Boolean(filters.city) ||
    Boolean(filters.min_score) ||
    Boolean(filters.channel) ||
    Boolean(filters.has_landing_page) ||
    Boolean(filters.landing_page_published) ||
    Boolean(filters.confidence) ||
    filters.sort !== "score";

  return (
    <div className="space-y-3 rounded-lg border bg-card p-3 shadow-sm">
      <div className="grid grid-cols-1 gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Busca por empresa */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por empresa..."
            value={filters.search}
            onChange={(e) => onFilterChange({ search: e.target.value })}
            className="pl-9 text-sm"
          />
        </div>

        {/* Nicho */}
        <Input
          placeholder="Filtrar por nicho..."
          value={filters.niche}
          onChange={(e) => onFilterChange({ niche: e.target.value })}
          className="text-sm"
        />

        {/* Cidade */}
        <Input
          placeholder="Filtrar por cidade..."
          value={filters.city}
          onChange={(e) => onFilterChange({ city: e.target.value })}
          className="text-sm"
        />

        {/* Ordenação */}
        <Select value={filters.sort} onValueChange={(val) => onFilterChange({ sort: val })}>
          <SelectTrigger className="text-sm">
            <SelectValue placeholder="Ordenar por" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="score">Maior score</SelectItem>
            <SelectItem value="reviews">Mais avaliações</SelectItem>
            <SelectItem value="recent">Mais recentes</SelectItem>
            <SelectItem value="name">Nome (A-Z)</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 lg:grid-cols-5 pt-1 border-t">
        {/* Score mínimo */}
        <Select
          value={filters.min_score || "all"}
          onValueChange={(val) => onFilterChange({ min_score: val === "all" ? "" : val })}
        >
          <SelectTrigger className="text-xs">
            <SelectValue placeholder="Score mínimo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Score (Todos)</SelectItem>
            <SelectItem value="50">Score ≥ 50</SelectItem>
            <SelectItem value="70">Score ≥ 70</SelectItem>
            <SelectItem value="85">Score ≥ 85</SelectItem>
          </SelectContent>
        </Select>

        {/* Canal disponível */}
        <Select
          value={filters.channel || "all"}
          onValueChange={(val) => onFilterChange({ channel: val === "all" ? "" : val })}
        >
          <SelectTrigger className="text-xs">
            <SelectValue placeholder="Canal de contato" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Canais (Todos)</SelectItem>
            <SelectItem value="whatsapp">WhatsApp disponível</SelectItem>
            <SelectItem value="phone">Telefone disponível</SelectItem>
          </SelectContent>
        </Select>

        {/* Possui protótipo */}
        <Select
          value={filters.has_landing_page || "all"}
          onValueChange={(val) => onFilterChange({ has_landing_page: val === "all" ? "" : val })}
        >
          <SelectTrigger className="text-xs">
            <SelectValue placeholder="Protótipo (LP)" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Protótipo (Todos)</SelectItem>
            <SelectItem value="true">Com protótipo</SelectItem>
            <SelectItem value="false">Sem protótipo</SelectItem>
          </SelectContent>
        </Select>

        {/* LP publicada */}
        <Select
          value={filters.landing_page_published || "all"}
          onValueChange={(val) =>
            onFilterChange({ landing_page_published: val === "all" ? "" : val })
          }
        >
          <SelectTrigger className="text-xs">
            <SelectValue placeholder="Status da LP" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">LP Status (Todos)</SelectItem>
            <SelectItem value="true">LP Publicada</SelectItem>
            <SelectItem value="false">LP em Rascunho</SelectItem>
          </SelectContent>
        </Select>

        {/* Confiança */}
        <Select
          value={filters.confidence || "all"}
          onValueChange={(val) => onFilterChange({ confidence: val === "all" ? "" : val })}
        >
          <SelectTrigger className="text-xs">
            <SelectValue placeholder="Confiança" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Confiança (Todas)</SelectItem>
            <SelectItem value="high">Alta</SelectItem>
            <SelectItem value="medium">Média</SelectItem>
            <SelectItem value="low">Baixa</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {hasActiveFilters && (
        <div className="flex justify-end pt-1">
          <Button variant="ghost" size="sm" onClick={onResetFilters} className="text-xs text-muted-foreground gap-1">
            <RotateCcw className="size-3" />
            Limpar filtros
          </Button>
        </div>
      )}
    </div>
  );
}
