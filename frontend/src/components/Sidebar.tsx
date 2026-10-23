"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
    LayoutDashboard,
    FileText,
    Bot,
    Search,
    BarChart3,
    Users,
    Settings,
    Sparkles
} from "lucide-react";
import { cn } from "@/lib/utils";

const navigation = [
    { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
    { name: "Documents", href: "/documents", icon: FileText },
    { name: "Agents", href: "/agents", icon: Bot },
    { name: "Query Lab", href: "/query", icon: Search },
    { name: "Analytics", href: "/analytics", icon: BarChart3 },
    { name: "Collaborate", href: "/collaborate", icon: Users },
    { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
    const pathname = usePathname();

    return (
        <div className="flex h-screen w-64 flex-col border-r bg-card border-border/40">
            {/* Logo */}
            <div className="flex h-16 items-center gap-2 border-b px-6 border-border/40">
                <Sparkles className="h-6 w-6 text-blue-500" />
                <span className="text-xl font-bold bg-gradient-to-r from-blue-500 to-purple-500 bg-clip-text text-transparent">
                    DataScout
                </span>
            </div>

            {/* Navigation */}
            <nav className="flex-1 space-y-1 p-4">
                {navigation.map((item) => {
                    const isActive = pathname?.startsWith(item.href);
                    return (
                        <Link
                            key={item.name}
                            href={item.href}
                            className={cn(
                                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                                isActive
                                    ? "bg-primary text-primary-foreground"
                                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                            )}
                        >
                            <item.icon className="h-5 w-5" />
                            {item.name}
                        </Link>
                    );
                })}
            </nav>

            {/* User Profile */}
            <div className="border-t p-4 border-border/40">
                <div className="flex items-center gap-3">
                    <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500" />
                    <div className="flex-1 text-sm">
                        <p className="font-medium">Enterprise User</p>
                        <p className="text-xs text-muted-foreground">admin@datascout.ai</p>
                    </div>
                </div>
            </div>
        </div>
    );
}
