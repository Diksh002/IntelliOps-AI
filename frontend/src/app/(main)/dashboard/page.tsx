"use client";

import { Card } from "@/components/ui/card";
import { TrendingUp, FileText, MessageSquare, Bot, ArrowUp } from "lucide-react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area
} from "recharts";
import { useQuery } from "@tanstack/react-query";
import { fetchStats, fetchAgentActivity } from "@/lib/api";
import { Skeleton } from "@/components/ui/skeleton";

const revenueData = [
    { month: "Jan", revenue: 186000 },
    { month: "Feb", revenue: 205000 },
    { month: "Mar", revenue: 237000 },
    { month: "Apr", revenue: 273000 },
    { month: "May", revenue: 209000 },
    { month: "Jun", revenue: 214000 },
];

const queryPerformanceData = [
    { hour: "00:00", queries: 12 },
    { hour: "04:00", queries: 8 },
    { hour: "08:00", queries: 45 },
    { hour: "12:00", queries: 72 },
    { hour: "16:00", queries: 58 },
    { hour: "20:00", queries: 34 },
];

interface ActivityItem {
    agent_name?: string;
    query?: string;
    timestamp: string | number | Date;
}

export default function DashboardPage() {
    const { data: stats, isLoading: statsLoading } = useQuery({
        queryKey: ['stats'],
        queryFn: fetchStats,
        refetchInterval: 5000 // Real-time updates
    });

    const { data: activity, isLoading: activityLoading } = useQuery<ActivityItem[]>({
        queryKey: ['activity'],
        queryFn: fetchAgentActivity,
        refetchInterval: 3000
    });

    if (statsLoading || activityLoading) {
        return (
            <div className="p-8 space-y-8">
                <Skeleton className="h-12 w-48" />
                <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    {[1, 2, 3, 4].map(i => <Skeleton key={i} className="h-32 w-full" />)}
                </div>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <Skeleton className="h-[300px] w-full" />
                    <Skeleton className="h-[300px] w-full" />
                </div>
            </div>
        );
    }

    const kpiData = [
        {
            title: "Total Revenue",
            value: stats?.revenue || "$2.4M",
            change: "+12.5%",
            trend: "up",
            icon: TrendingUp
        },
        {
            title: "Documents Processed",
            value: stats?.documents || "0",
            change: "+23.1%",
            trend: "up",
            icon: FileText
        },
        {
            title: "Active Queries",
            value: stats?.queries || "0",
            change: "+8.3%",
            trend: "up",
            icon: MessageSquare
        },
        {
            title: "Agents Running",
            value: stats?.agents_active || "4",
            change: "100%",
            trend: "up",
            icon: Bot
        },
    ];

    return (
        <div className="p-8 space-y-8">
            {/* Header */}
            <div>
                <h1 className="text-3xl font-bold">Dashboard</h1>
                <p className="text-muted-foreground">Welcome back to DataScout Enterprise</p>
            </div>

            {/* KPI Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                {kpiData.map((kpi) => (
                    <Card key={kpi.title} className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                        <div className="flex items-start justify-between">
                            <div className="space-y-1">
                                <p className="text-sm text-muted-foreground">{kpi.title}</p>
                                <p className="text-3xl font-bold">{kpi.value}</p>
                                <div className="flex items-center gap-1 text-sm text-green-500">
                                    <ArrowUp className="h-4 w-4" />
                                    <span>{kpi.change}</span>
                                </div>
                            </div>
                            <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center">
                                <kpi.icon className="h-6 w-6 text-primary" />
                            </div>
                        </div>
                    </Card>
                ))}
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Revenue Chart */}
                <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                    <div className="mb-4">
                        <h3 className="text-lg font-semibold">Revenue Trends</h3>
                        <p className="text-sm text-muted-foreground">Monthly revenue performance</p>
                    </div>
                    <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={revenueData}>
                            <defs>
                                <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                            <XAxis dataKey="month" stroke="#888" />
                            <YAxis stroke="#888" />
                            <Tooltip
                                contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '8px' }}
                                formatter={(value) => (typeof value === "number" ? `$${(value / 1000).toFixed(0)}k` : "")}
                            />
                            <Area
                                type="monotone"
                                dataKey="revenue"
                                stroke="#3b82f6"
                                strokeWidth={2}
                                fill="url(#colorRevenue)"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </Card>

                {/* Query Performance */}
                <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                    <div className="mb-4">
                        <h3 className="text-lg font-semibold">Query Performance</h3>
                        <p className="text-sm text-muted-foreground">Queries over the last 24 hours</p>
                    </div>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={queryPerformanceData}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                            <XAxis dataKey="hour" stroke="#888" />
                            <YAxis stroke="#888" />
                            <Tooltip
                                contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '8px' }}
                            />
                            <Bar dataKey="queries" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                </Card>
            </div>

            {/* Activity Feed */}
            <div className="grid grid-cols-1 gap-6">
                <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                    <div className="mb-4">
                        <h3 className="text-lg font-semibold">Live Activity Feed</h3>
                        <p className="text-sm text-muted-foreground">Real-time agent and user activity</p>
                    </div>
                    <div className="space-y-4">
                        {activity?.map((act: ActivityItem, index: number) => (
                            <div key={index} className="flex items-start gap-3 pb-3 border-b border-border/20 last:border-0">
                                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex-shrink-0" />
                                <div className="flex-1 min-w-0">
                                    <p className="text-sm">
                                        <span className="font-medium">{act.agent_name || "System"}</span>{" "}
                                        <span className="text-muted-foreground">processed query: {act.query}</span>
                                    </p>
                                    <p className="text-xs text-muted-foreground">{new Date(act.timestamp).toLocaleTimeString()}</p>
                                </div>
                            </div>
                        ))}
                        {!activity?.length && <p className="text-sm text-muted-foreground">No recent activity.</p>}
                    </div>
                </Card>
            </div>
        </div>
    );
}
