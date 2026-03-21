import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  Building2,
  FileText,
  Search,
  Shield,
  MessageSquare,
  Settings,
  LogOut,
  ClipboardList,
  Bell,
  Cpu,
  TrendingUp,
  BarChart3,
  Target,
  BookOpen,
  CheckCircle,
  Users,
  Link2,
  Layers,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';

interface NavItem {
  name: string;
  href: string;
  icon: React.ElementType;
}

const navigation: NavItem[] = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Agents', href: '/agents', icon: Cpu },
  { name: 'Risk', href: '/risk', icon: TrendingUp },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Playbooks', href: '/playbooks', icon: BookOpen },
  { name: 'Approved AI', href: '/approved-vendors', icon: CheckCircle },
  { name: 'BPO', href: '/bpo', icon: Users },
  { name: 'Integrations', href: '/integrations', icon: Link2 },
  { name: 'Competition', href: '/competition', icon: Target },
  { name: 'Vendors', href: '/vendors', icon: Building2 },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Analysis', href: '/analysis', icon: Shield },
  { name: 'Frameworks', href: '/frameworks', icon: Layers },
  { name: 'Remediation', href: '/remediation', icon: ClipboardList },
  { name: 'Monitoring', href: '/monitoring', icon: Bell },
  { name: 'Query', href: '/query', icon: MessageSquare },
  { name: 'Search', href: '/search', icon: Search },
];

export function Sidebar() {
  const location = useLocation();
  const { user, logout } = useAuthStore();

  return (
    <div className="flex flex-col h-[calc(100vh-2rem)] w-72 m-4 rounded-2xl glass-panel-liquid relative overflow-hidden transition-all duration-300 z-50">

      {/* Visual Depth Elements */}
      <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-50" />
      <div className="absolute bottom-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent opacity-30" />

      {/* Logo Section */}
      <div className="flex h-24 items-center gap-4 px-6 select-none relative">
        <div className="absolute inset-x-6 bottom-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />

        <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-white/10 to-white/5 border border-white/10 shadow-lg group-hover:scale-105 transition-transform duration-500">
          <Shield className="h-5 w-5 text-obsidian-teal drop-shadow-[0_0_8px_rgba(0,212,170,0.5)]" />
        </div>

        <div className="flex flex-col justify-center">
          <span className="text-lg font-bold tracking-tight text-white font-heading">
            VendorAudit<span className="text-obsidian-teal">AI</span>
          </span>
          <span className="text-[10px] uppercase tracking-[0.2em] text-muted-foreground font-medium">
            Ent. Risk OS
          </span>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1.5 px-4 py-6 overflow-y-auto custom-scrollbar">
        {navigation.map((item) => {
          const isActive = location.pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              to={item.href}
              className={cn(
                'group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-300 relative overflow-hidden',
                isActive
                  ? 'text-white bg-white/5 shadow-[inset_0_1px_0_0_rgba(255,255,255,0.05)] border border-white/5'
                  : 'text-muted-foreground hover:text-white hover:bg-white/[0.02] border border-transparent'
              )}
            >
              <item.icon className={cn(
                "h-4 w-4 transition-all duration-300",
                isActive ? "text-obsidian-teal drop-shadow-[0_0_6px_rgba(0,212,170,0.4)]" : "text-slate-400 group-hover:text-obsidian-teal"
              )} />
              <span className="relative z-10 tracking-wide">{item.name}</span>

              {isActive && (
                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-3/5 bg-obsidian-teal rounded-r-full shadow-[0_0_10px_#00D4AA] opacity-80" />
              )}
            </Link>
          );
        })}
      </nav>

      {/* User section */}
      <div className="p-4 mt-auto">
        <div className="glass-panel-liquid rounded-xl p-3 border border-white/5">
          <div className="flex items-center gap-3 mb-3">
            <div className="relative h-9 w-9 rounded-full bg-gradient-to-tr from-obsidian-teal to-obsidian-blue p-[1px] shadow-lg">
              <div className="h-full w-full rounded-full bg-black/50 backdrop-blur-sm flex items-center justify-center text-xs font-bold text-white">
                {(user as any)?.user_metadata?.full_name?.charAt(0) || 'U'}
              </div>
              <div className="absolute bottom-0 right-0 h-2.5 w-2.5 rounded-full bg-emerald-500 border-2 border-black" />
            </div>

            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-white truncate font-heading">
                {(user as any)?.user_metadata?.full_name || 'Admin User'}
              </p>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                Authenticated
              </p>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <Link
              to="/settings"
              className="flex items-center justify-center gap-2 rounded-lg bg-white/5 px-3 py-2 text-xs font-medium text-slate-300 hover:text-white hover:bg-white/10 transition-colors"
            >
              <Settings className="h-3.5 w-3.5" />
              Config
            </Link>
            <button
              onClick={logout}
              className="flex items-center justify-center gap-2 rounded-lg bg-red-500/10 px-3 py-2 text-xs font-medium text-red-400 hover:bg-red-500/20 hover:text-red-300 transition-colors"
            >
              <LogOut className="h-3.5 w-3.5" />
              Logout
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
