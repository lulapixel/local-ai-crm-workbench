import { Search, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { DailyCategoryTab, DailyFiltersState } from "./types";

interface DailyOutreachFiltersProps {
  filters: DailyFiltersState;
  onFilterChange: (key: keyof DailyFiltersState, value: any) => void;
  onClearFilters: () => void;
}

export function DailyOutreachFilters({
  filters,
  onFilterChange,
  onClearFilters,
}: DailyOutreachFiltersProps) {
  const tabs: Array<{ id: DailyCategoryTab; label: string }> = [
    { id: "all", label: "Tudo" },
    { id: "overdue", label: "Atrasados" },
    { id: "today", label: "Prontos Hoje" },
    { id: "new", label: "Novos Contatos" },
    { id: "paused", label: "Pausados" },
    { id: "upcoming", label: "Próximos" },
    { id: "replied", label: "Respondidos" },
  ];

  const hasActiveFilters =
    filters.category !== "all" ||
    Boolean(filters.search) ||
    Boolean(filters.niche) ||
    Boolean(filters.city) ||
    Boolean(filters.min_score) ||
    filters.channel !== "all";

  return (
    <div className="space-y-4 rounded-xl border border-border bg-card p-4">
      {/* Category Tabs */}
      <div className="flex overflow-x-auto gap-1 border-b pb-3 no-scrollbar">
        {tabs.map((t) => {
          const isActive = filters.category === t.id;
          return (
            <button
              key={t.id}
              onClick={() => onFilterChange("category", t.id)}
              className={`whitespace-nowrap rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {t.label}
            </button>
          );
        })}
      </div>

      {/* Filter Inputs Row */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
          <Input
            placeholder="Buscar por nome, nicho, cidade..."
            value={filters.search}
            onChange={(e) => onFilterChange("search", e.target.value)}
            className="pl-8 text-xs h-9"
          />
        </div>

        {/* Min Score Select */}
        <Select
          value={filters.min_score || "all"}
          onValueChange={(val) => onFilterChange("min_score", val === "all" ? "" : val)}
        >
          <SelectTrigger className="h-9 text-xs">
            <SelectValue placeholder="Score mínimo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Score: Todos</SelectItem>
            <SelectItem value="80">★ 80+ pts (Excelente)</SelectItem>
            <SelectItem value="70">★ 70+ pts (Alto)</SelectItem>
            <SelectItem value="50">★ 50+ pts (Médio)</SelectItem>
          </SelectContent>
        </Select>

        {/* Channel Filter */}
        <Select
          value={filters.channel || "all"}
          onValueChange={(val) => onFilterChange("channel", val)}
        >
          <SelectTrigger className="h-9 text-xs">
            <SelectValue placeholder="Canal de contato" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Canal: Todos</SelectItem>
            <SelectItem value="whatsapp">📱 WhatsApp</SelectItem>
          </SelectContent>
        </Select>

        {/* Clear Filters Button */}
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearFilters}
            className="h-9 text-xs text-muted-foreground hover:text-foreground gap-1"
          >
            <X className="size-3.5" />
            <span>Limpar filtros</span>
          </Button>
        )}
      </div>
    </div>
  );
}
