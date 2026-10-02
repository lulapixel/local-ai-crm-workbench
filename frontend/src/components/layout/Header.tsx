import { Link, NavLink, useLocation } from "react-router-dom"
import { Activity, Bot, BookOpen, FileSearch, LayoutDashboard, ListTodo, MapPin, Menu, Plus, Search, Send, Settings, Trash2, BarChart3 } from "lucide-react"
import { ThemeToggle } from "@/components/layout/ThemeToggle"
import "@/pages/workspace.css"
interface HeaderProps { onNovaBusca?: () => void; onVerIgnorados?: () => void }
const principal = [
  { to: "/", label: "Mesa do gestor", icon: LayoutDashboard }, { to: "/operacao", label: "Minha sessão", icon: Activity },
  { to: "/pesquisa", label: "Mesa de pesquisa", icon: FileSearch }, { to: "/leads", label: "Leads do Maps", icon: MapPin },
  { to: "/instagram", label: "Instagram", icon: Search }, { to: "/tarefas", label: "Oportunidades", icon: ListTodo },
  { to: "/outreach/hoje", label: "Prospecção do dia", icon: Send }, { to: "/bot", label: "Bot e automação", icon: Bot },
]
const secondary = [
  { to: "/abordagens", label: "Abordagens", icon: Send }, { to: "/analytics", label: "Resultados", icon: BarChart3 },
  { to: "/documentacao", label: "Documentação", icon: BookOpen }, { to: "/configuracoes", label: "Configurações", icon: Settings },
]
export function Header({ onNovaBusca, onVerIgnorados }: HeaderProps) {
  const location = useLocation()
  const title = [...principal, ...secondary].find(item => item.to === location.pathname)?.label ?? "ProspectOS"
  const links = (items: typeof principal) => items.map(({ to, label, icon: Icon }) => <NavLink end={to === "/"} to={to} key={to} className={({ isActive }) => isActive ? "workspace-nav-link active" : "workspace-nav-link"} onClick={e => e.currentTarget.closest("details")?.removeAttribute("open")}><Icon size={17} /><span>{label}</span></NavLink>)
  return <header className="workspace-header">
    <aside className="workspace-sidebar" aria-label="Navegação do workspace"><Link className="workspace-brand" to="/"><img src="/logo-icon.svg" alt="" /><span><strong>ProspectOS</strong><small>LOCAL WORKBENCH</small></span></Link><p className="workspace-nav-label">SEU TRABALHO</p><nav>{links(principal)}</nav><p className="workspace-nav-label">ACOMPANHAMENTO</p><nav>{links(secondary)}</nav><div className="workspace-sidebar-foot"><span className="workspace-local-dot" /> Base local · revisão humana<small>Contexto antes de volume.</small></div></aside>
    <div className="workspace-topbar"><div className="workspace-breadcrumb"><details className="workspace-mobile-menu"><summary aria-label="Abrir navegação"><Menu size={20} /></summary><nav aria-label="Navegação móvel">{links([...principal, ...secondary])}</nav></details><Link className="workspace-mobile-brand" to="/"><img src="/logo-icon.svg" alt="ProspectOS" /></Link><span>Workspace <b>/</b> <strong>{title}</strong></span></div><div className="workspace-top-actions"><button className="workspace-search-button" onClick={() => window.dispatchEvent(new Event("prospectos:open-command"))}><Search size={16} /><span>Buscar</span><kbd>Ctrl K</kbd></button>{onVerIgnorados && <button className="workspace-icon-button" title="Ver ignorados" aria-label="Ver ignorados" onClick={onVerIgnorados}><Trash2 size={16} /></button>}{onNovaBusca && <button className="desk-primary" onClick={onNovaBusca}><Plus size={16} /><span>Nova busca</span></button>}<ThemeToggle /></div></div>
  </header>
}
