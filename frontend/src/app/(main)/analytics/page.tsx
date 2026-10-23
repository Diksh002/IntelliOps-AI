"use client";

import { useState, useEffect } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { TrendingUp, Download, Activity, Zap, CheckCircle2, BarChart3 } from "lucide-react";
import { toast } from "sonner";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";

interface AnalyticsSummary {
    total_queries: number;
    avg_latency_ms: number;
    recent_queries_24h: number;
    success_rate: number;
    queries_by_agent: Array<{ agent: string; count: number }>;
}

export default function AnalyticsPage() {
    const [analytics, setAnalytics] = useState<AnalyticsSummary | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchAnalytics();
    }, []);

    const fetchAnalytics = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/analytics/summary`);
            if (!response.ok) throw new Error('Failed to fetch analytics');
            const data = await response.json();
            setAnalytics(data);
        } catch (error) {
            console.error('Error fetching analytics:', error);
            toast.error('Failed to load analytics data');
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500 mx-auto"></div>
                    <p className="mt-4 text-muted-foreground">Loading analytics...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Analytics Center</h1>
                    <p className="text-muted-foreground">Real-time insights from your agent swarm</p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" className="gap-2" onClick={() => fetchAnalytics()}>
                        <Activity className="h-4 w-4" />
                        Refresh
                    </Button>
                    <Button className="gap-2" onClick={() => toast.success("Report downloaded successfully")}>
                        <Download className="h-4 w-4" />
                        Export Report
                    </Button>
                </div>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="p-4 bg-gradient-to-br from-blue-500/10 to-blue-600/5 border-blue-500/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Total Queries</p>
                            <p className="text-2xl font-bold">{analytics?.total_queries || 0}</p>
                            <p className="text-xs text-blue-400 mt-1">All time</p>
                        </div>
                        <BarChart3 className="h-8 w-8 text-blue-500" />
                    </div>
                </Card>

                <Card className="p-4 bg-gradient-to-br from-purple-500/10 to-purple-600/5 border-purple-500/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Avg Latency</p>
                            <p className="text-2xl font-bold">{analytics?.avg_latency_ms.toFixed(0) || 0}ms</p>
                            <p className="text-xs text-purple-400 mt-1">Response time</p>
                        </div>
                        <Zap className="h-8 w-8 text-purple-500" />
                    </div>
                </Card>

                <Card className="p-4 bg-gradient-to-br from-green-500/10 to-green-600/5 border-green-500/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Success Rate</p>
                            <p className="text-2xl font-bold">{analytics?.success_rate || 0}%</p>
                            <p className="text-xs text-green-400 mt-1">Completed</p>
                        </div>
                        <CheckCircle2 className="h-8 w-8 text-green-500" />
                    </div>
                </Card>

                <Card className="p-4 bg-gradient-to-br from-amber-500/10 to-amber-600/5 border-amber-500/20">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="text-sm text-muted-foreground">Last 24h</p>
                            <p className="text-2xl font-bold">{analytics?.recent_queries_24h || 0}</p>
                            <p className="text-xs text-amber-400 mt-1">Recent activity</p>
                        </div>
                        <TrendingUp className="h-8 w-8 text-amber-500" />
                    </div>
                </Card>
            </div>

            {/* Agent Performance Chart */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                <div className="mb-4">
                    <h3 className="text-lg font-semibold">Agent Performance</h3>
                    <p className="text-sm text-muted-foreground">Queries handled by each agent</p>
                </div>
                <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={analytics?.queries_by_agent || []}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                        <XAxis dataKey="agent" stroke="#888" />
                        <YAxis stroke="#888" />
                        <Tooltip
                            contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '8px' }}
                        />
                        <Bar dataKey="count" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                    </BarChart>
                </ResponsiveContainer>
            </Card>

            {/* AI Insights */}
            <Card className="p-6 bg-gradient-to-br from-blue-500/10 to-purple-500/10 border-blue-500/20">
                <h3 className="text-lg font-semibold mb-3">🤖 System Insights</h3>
                <div className="space-y-3">
                    <div className="p-3 bg-card/50 rounded-lg">
                        <p className="text-sm font-medium">📊 Performance Status</p>
                        <p className="text-sm text-muted-foreground mt-1">
                            {analytics && analytics.avg_latency_ms < 1000
                                ? "System is performing optimally with sub-second response times."
                                : "Response times are within acceptable range."}
                        </p>
                    </div>
                    <div className="p-3 bg-card/50 rounded-lg">
                        <p className="text-sm font-medium">✅ Reliability</p>
                        <p className="text-sm text-muted-foreground mt-1">
                            {analytics && analytics.success_rate > 95
                                ? "Excellent success rate! The agent swarm is highly reliable."
                                : "Success rate is good. Monitor for any recurring failures."}
                        </p>
                    </div>
                    <div className="p-3 bg-card/50 rounded-lg">
                        <p className="text-sm font-medium">📈 Activity Trend</p>
                        <p className="text-sm text-muted-foreground mt-1">
                            {analytics && analytics.recent_queries_24h > 0
                                ? `${analytics.recent_queries_24h} queries processed in the last 24 hours.`
                                : "No recent activity detected. System is ready for queries."}
                        </p>
                    </div>
                </div>
            </Card>
        </div>
    );
}
