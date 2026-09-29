import { Link, NavLink } from "react-router-dom"
import { BookOpen, ChevronDown, LayoutDashboard, ListTodo, MapPin, Plus, Send, Settings, Trash2 } from "lucide-react"
import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { ThemeToggle } from "@/components/layout/ThemeToggle"
import { InstagramIcon } from "@/components/icons/InstagramIcon"

interface HeaderProps {
  onNovaBusca?: () => void
  onVerIgnorados?: () => void
}

const PRINCIPAIS = [
  { to: "/", label: "Painel", icon: LayoutDashboard },
  { to: "/tarefas", label: "Oportunidades", icon: ListTodo },
  { to: "/leads", label: "Leads", icon: MapPin },
  { to: "/outreach/hoje", label: "Prospecção", icon: Send },
]

export function Header({ onNovaBusca, onVerIgnorados }: HeaderProps) {
  return (
    <header className="sticky top-0 z-20 border-b border-[#d8e5e9] bg-white/95 shadow-[0_2px_18px_#153c5810] backdrop-blur dark:border-border dark:bg-background/95">
      <div className="mx-auto flex w-full max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6 lg:px-8">
        <Link to="/" className="flex min-w-0 shrink-0 items-center gap-2.5" aria-label="ProspectOS, voltar ao painel">
          <img src="/logo-icon.svg" alt="" className="size-9" />
          <span className="hidden flex-col leading-none min-[520px]:flex"><strong className="text-[1.03rem] font-extrabold tracking-[-.05em] text-[#19334a] dark:text-foreground">ProspectOS</strong><small className="mt-1 hidden text-[.52rem] font-bold uppercase tracking-[.21em] text-[#3a8290] sm:block">WORKBENCH</small></span>
        </Link>
        <nav aria-label="Navegação principal" className="flex items-center gap-0.5 md:gap-1">
          {PRINCIPAIS.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === "/"} title={label} className={({ isActive }) => cn(
              "flex min-h-10 items-center gap-1.5 rounded-lg px-2 text-xs font-semibold transition-colors sm:px-2.5 lg:text-sm",
              to === "/outreach/hoje" && "max-[390px]:hidden",
              isActive ? "bg-[#e3f2f3] text-[#166f7b] dark:bg-accent dark:text-foreground" : "text-[#6c8593] hover:bg-[#eef5f6] hover:text-[#19334a] dark:text-muted-foreground dark:hover:bg-accent"
            )}><Icon size={16} /><span className="hidden lg:inline">{label}</span></NavLink>
          ))}
          <details className="group relative">
            <summary className="flex min-h-10 cursor-pointer list-none items-center gap-1 rounded-lg px-2 text-xs font-semibold text-[#6c8593] hover:bg-[#eef5f6] hover:text-[#19334a] dark:text-muted-foreground dark:hover:bg-accent sm:px-2.5 lg:text-sm [&::-webkit-details-marker]:hidden" aria-label="Mais páginas">
              <span className="hidden sm:inline">Mais</span><ChevronDown size={14} className="transition-transform group-open:rotate-180" />
            </summary>
            <div className="absolute right-0 top-11 z-30 flex w-56 flex-col gap-1 rounded-xl border border-border bg-card p-2 shadow-xl">
              <Link to="/instagram" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"><InstagramIcon className="size-4" /> Instagram</Link>
              <Link to="/outreach/hoje" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"><Send size={16} /> Prospecção do dia</Link>
              <Link to="/abordagens" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"><Send size={16} /> Abordagens</Link>
              <Link to="/analytics" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent">Resultados</Link>
              <Link to="/documentacao" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"><BookOpen size={16} /> Documentação</Link>
              <Link to="/configuracoes" className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-accent"><Settings size={16} /> Configurações</Link>
            </div>
          </details>
          {onVerIgnorados && <Button variant="ghost" size="icon" title="Ver ignorados" aria-label="Ver ignorados" onClick={onVerIgnorados}><Trash2 size={16} /></Button>}
          {onNovaBusca && <Button size="sm" onClick={onNovaBusca} className="h-9 bg-[#217d87] px-2 text-white hover:bg-[#17646e] sm:px-3"><Plus size={16} /><span className="hidden sm:inline">Nova busca</span></Button>}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  )
}
