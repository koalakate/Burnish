import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

const navItems = [
  { href: "/", label: "Home", icon: "◆" },
  { href: "/decks", label: "Decks", icon: "▦" },
  { href: "/brand", label: "Brand", icon: "◉" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex h-screen overflow-hidden">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 border-r border-border/50 bg-card flex flex-col">
        {/* Logo */}
        <div className="px-5 py-5 border-b border-border/50">
          <h1 className="font-mono text-lg font-medium tracking-tight">
            burnish<span className="text-cyan-400">.</span>
          </h1>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-3 py-4 space-y-1">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="flex items-center gap-3 px-3 py-2 text-sm text-muted-foreground rounded-md
                         hover:bg-accent hover:text-foreground transition-colors"
            >
              <span className="text-xs opacity-60">{item.icon}</span>
              {item.label}
            </Link>
          ))}
        </nav>

        {/* User */}
        <div className="px-5 py-4 border-t border-border/50">
          <UserButton />
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="px-8 py-6">{children}</div>
      </main>
    </div>
  );
}
