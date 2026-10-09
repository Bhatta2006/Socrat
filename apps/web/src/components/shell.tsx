'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState, type ReactNode } from 'react';
import { useTheme } from 'next-themes';
import {
  Building2,
  CalendarDays,
  ChartLine,
  Flame,
  Home,
  Library,
  LogOut,
  Monitor,
  Moon,
  Settings,
  Sparkles,
  Sun,
} from 'lucide-react';
import { api } from '@/lib/api';
import { useSession } from '@/lib/session';
import type { Today } from '@/lib/types';
import { cn } from '@/lib/utils';
import { CommandMenu } from '@/components/command-menu';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Separator } from '@/components/ui/separator';
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from '@/components/ui/sidebar';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';

const NAV = [
  { href: '/today', label: 'Today', icon: Home },
  { href: '/plan', label: 'Plan', icon: CalendarDays },
  { href: '/library', label: 'Library', icon: Library },
  { href: '/progress', label: 'Progress', icon: ChartLine },
];
const MORE = [
  { href: '/companies', label: 'Company questions', icon: Building2 },
  { href: '/settings', label: 'Settings', icon: Settings },
];
const MOBILE = [...NAV, { href: '/settings', label: 'Settings', icon: Settings }];

function Wordmark({ className, compact = false }: { className?: string; compact?: boolean }) {
  return (
    <span className={cn('inline-flex items-center gap-2 font-semibold tracking-tight', className)}>
      <span className="grid size-7 flex-none place-items-center rounded-lg bg-primary text-primary-foreground shadow-sm">
        <Sparkles className="size-4" aria-hidden="true" />
      </span>
      {compact ? null : <span className="wordmark-label">Socrat</span>}
    </span>
  );
}

function DevBanner() {
  const { features } = useSession();
  if (!features?.demo_mode && !features?.dev_login) return null;
  return (
    <div className="border-b border-warning/30 bg-warning/15 px-4 py-1 text-center text-xs text-warning-foreground dark:text-warning">
      Local development build — sign-in is simulated and code runs without a secure sandbox.
    </div>
  );
}

function ThemeItems() {
  const { theme, setTheme } = useTheme();
  return (
    <DropdownMenuRadioGroup value={theme ?? 'system'} onValueChange={setTheme}>
      <DropdownMenuRadioItem value="light"><Sun /> Light</DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="dark"><Moon /> Dark</DropdownMenuRadioItem>
      <DropdownMenuRadioItem value="system"><Monitor /> System</DropdownMenuRadioItem>
    </DropdownMenuRadioGroup>
  );
}

function UserMenu() {
  const { profile, signOut } = useSession();
  const router = useRouter();
  const name = profile?.display_name || 'Learner';
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="rounded-full" aria-label="Account menu">
          <Avatar className="size-8">
            <AvatarFallback className="bg-primary/15 text-xs font-semibold text-primary">{name.slice(0, 2).toUpperCase()}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        <DropdownMenuLabel className="font-normal">
          <p className="text-sm font-medium">{name}</p>
          <p className="text-xs text-muted-foreground">Signed in</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild><Link href="/settings"><Settings /> Settings</Link></DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-xs text-muted-foreground">Theme</DropdownMenuLabel>
        <ThemeItems />
        <DropdownMenuSeparator />
        <DropdownMenuItem onSelect={async () => { await signOut(); router.replace('/login'); }}>
          <LogOut /> Sign out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** Streak and today's minutes, always in view: loss aversion and the goal gradient at a glance. */
function Momentum() {
  const pathname = usePathname();
  const [today, setToday] = useState<Today | null>(null);
  useEffect(() => {
    api.get<Today>('/today').then(setToday).catch(() => undefined);
  }, [pathname]);
  if (!today) return null;
  const percent = today.minutes.goal ? Math.min(100, Math.round((100 * today.minutes.done) / today.minutes.goal)) : 0;
  const lit = today.streak.studied_today;
  return (
    <div className="flex items-center gap-1.5">
      <Tooltip>
        <TooltipTrigger asChild>
          <Link
            href="/progress"
            className={cn(
              'inline-flex h-8 items-center gap-1.5 rounded-full border px-2.5 text-sm font-semibold tabular-nums transition-colors',
              lit ? 'border-streak/30 bg-streak/10 text-streak' : 'text-muted-foreground hover:text-foreground',
            )}
            aria-label={`${today.streak.current} day streak`}
          >
            <Flame className={cn('size-4', lit && 'fill-current')} aria-hidden="true" />
            {today.streak.current}
          </Link>
        </TooltipTrigger>
        <TooltipContent>{lit ? 'Streak secured for today' : 'Study today to keep your streak'}</TooltipContent>
      </Tooltip>
      <Tooltip>
        <TooltipTrigger asChild>
          <Link href="/today" className="hidden h-8 items-center gap-2 rounded-full border px-2.5 text-xs font-medium text-muted-foreground hover:text-foreground sm:inline-flex">
            <span className="relative h-1.5 w-12 overflow-hidden rounded-full bg-muted">
              <span className="absolute inset-y-0 left-0 rounded-full bg-primary transition-all" style={{ width: `${percent}%` }} />
            </span>
            <span className="tabular-nums">{today.minutes.done}/{today.minutes.goal}m</span>
          </Link>
        </TooltipTrigger>
        <TooltipContent>Today&apos;s study goal</TooltipContent>
      </Tooltip>
    </div>
  );
}

function NavGroup({ label, items, current }: { label: string; items: typeof NAV; current: (href: string) => boolean }) {
  return (
    <SidebarGroup>
      <SidebarGroupLabel>{label}</SidebarGroupLabel>
      <SidebarGroupContent>
        <SidebarMenu>
          {items.map(item => (
            <SidebarMenuItem key={item.href}>
              <SidebarMenuButton asChild isActive={current(item.href)} tooltip={item.label}>
                <Link href={item.href} aria-current={current(item.href) ? 'page' : undefined}>
                  <item.icon /> <span>{item.label}</span>
                </Link>
              </SidebarMenuButton>
            </SidebarMenuItem>
          ))}
        </SidebarMenu>
      </SidebarGroupContent>
    </SidebarGroup>
  );
}

function AppSidebar({ current }: { current: (href: string) => boolean }) {
  return (
    <Sidebar collapsible="icon">
      <SidebarHeader className="h-14 justify-center px-3">
        <Link href="/today" aria-label="Socrat home" className="[&_.wordmark-label]:group-data-[collapsible=icon]:hidden">
          <Wordmark className="text-base" />
        </Link>
      </SidebarHeader>
      <SidebarContent>
        <nav aria-label="Main">
          <NavGroup label="Learn" items={NAV} current={current} />
          <NavGroup label="More" items={MORE} current={current} />
        </nav>
      </SidebarContent>
      <SidebarFooter className="group-data-[collapsible=icon]:hidden">
        <div className="rounded-lg border bg-card p-3 text-xs text-muted-foreground">
          <p className="mb-1 font-medium text-foreground">Tip</p>
          Press <kbd className="rounded border bg-muted px-1 font-mono">⌘K</kbd> to jump to any lesson or problem.
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}

function MobileNav({ current }: { current: (href: string) => boolean }) {
  return (
    <nav aria-label="Main" className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t bg-background/90 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden">
      {MOBILE.map(item => (
        <Link
          key={item.href}
          href={item.href}
          aria-current={current(item.href) ? 'page' : undefined}
          className={cn('grid justify-items-center gap-0.5 py-2 text-[11px] font-medium text-muted-foreground', current(item.href) && 'text-primary')}
        >
          <item.icon className="size-5" aria-hidden="true" />
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

function MarketingShell({ children }: { children: ReactNode }) {
  const { profile } = useSession();
  const pathname = usePathname();
  return (
    <>
      <a href="#main" className="skip-link">Skip to content</a>
      <DevBanner />
      <header className="sticky top-0 z-40 bg-background/80 backdrop-blur-md supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
          <Link href={profile ? '/today' : '/'} aria-label="Socrat home"><Wordmark /></Link>
          <nav className="flex items-center gap-1" aria-label="Site">
            {pathname === '/' ? <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex"><a href="#how">How it works</a></Button> : null}
            {pathname === '/' ? <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex"><a href="#courses">Courses</a></Button> : null}
            {profile ? (
              <Button asChild size="sm"><Link href="/today">Open app</Link></Button>
            ) : pathname !== '/login' ? (
              <>
                <Button asChild variant="ghost" size="sm"><Link href="/login">Sign in</Link></Button>
                <Button asChild size="sm"><Link href="/login">Get started</Link></Button>
              </>
            ) : null}
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="outline-none">{children}</main>
    </>
  );
}

export default function Shell({ children }: { children: ReactNode }) {
  const { profile } = useSession();
  const pathname = usePathname();
  const learning = Boolean(profile?.enrollment && profile.enrollment.status === 'active');
  const current = (href: string) =>
    pathname === href || pathname.startsWith(`${href}/`) || (href === '/library' && pathname.startsWith('/companies'));

  if (!learning) return <MarketingShell>{children}</MarketingShell>;

  return (
    <SidebarProvider>
      <a href="#main" className="skip-link">Skip to content</a>
      <AppSidebar current={current} />
      <SidebarInset id="main" tabIndex={-1} className="min-w-0 outline-none">
        <DevBanner />
        <header className="sticky top-0 z-30 flex h-14 items-center gap-2 border-b bg-background/80 px-3 backdrop-blur-md supports-[backdrop-filter]:bg-background/60 sm:px-4">
          <SidebarTrigger className="hidden md:inline-flex" />
          <Link href="/today" className="md:hidden" aria-label="Socrat home"><Wordmark compact /></Link>
          <Separator orientation="vertical" className="mx-1 hidden h-5 md:block" />
          <div className="min-w-0 flex-1"><CommandMenu /></div>
          <div className="ml-auto flex items-center gap-1.5">
            <Momentum />
            <UserMenu />
          </div>
        </header>
        <div className="min-w-0 flex-1">{children}</div>
      </SidebarInset>
      <MobileNav current={current} />
    </SidebarProvider>
  );
}
