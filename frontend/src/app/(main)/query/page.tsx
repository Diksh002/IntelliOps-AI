"use client";

import { useState, useEffect } from "react";
import { ChatInterface } from "@/components/ChatInterface";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { History, Loader2, RefreshCw, Sparkles } from "lucide-react";
import { toast } from "sonner";

interface QueryHistoryItem {
    id: number;
    query: string;
    result: string;
    timestamp: string;
}

const quickTemplates = [
    { label: "📊 Revenue by region", query: "Show me revenue breakdown by region" },
    { label: "📈 Sales trends", query: "Show sales trends for the last 6 months" },
    { label: "💰 Top transactions", query: "What are the top 10 transactions?" },
    { label: "👥 Payroll summary", query: "Show me the payroll summary by department" },
    { label: "📉 Monthly comparison", query: "Compare this month's sales to last month" },
];

export default function QueryPage() {
    const [queryHistory, setQueryHistory] = useState<QueryHistoryItem[]>([]);
    const [loading, setLoading] = useState(true);
    const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null);

    useEffect(() => {
        fetchHistory();
    }, []);

    // Listen for new messages to refresh history
    useEffect(() => {
        const interval = setInterval(() => {
            fetchHistory();
        }, 30000); // Refresh every 30 seconds
        return () => clearInterval(interval);
    }, []);

    const fetchHistory = async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/history`);
            if (!response.ok) throw new Error('Failed to fetch history');
            const data = await response.json();
            setQueryHistory(data);
        } catch (error) {
            console.error('Error fetching history:', error);
        } finally {
            setLoading(false);
        }
    };

    const getTimeAgo = (timestamp: string) => {
        const date = new Date(timestamp);
        const now = new Date();
        const diffMs = now.getTime() - date.getTime();
        const diffMins = Math.floor(diffMs / 60000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins} min ago`;
        const diffHours = Math.floor(diffMins / 60);
        if (diffHours < 24) return `${diffHours}h ago`;
        const diffDays = Math.floor(diffHours / 24);
        return `${diffDays}d ago`;
    };

    const handleTemplateClick = (query: string) => {
        setSelectedTemplate(query);
        toast.info(`Template selected: "${query.substring(0, 30)}..."`);
        // Copy to clipboard for easy paste
        navigator.clipboard.writeText(query);
        toast.success("Copied to clipboard! Paste in chat to use.");
    };

    return (
        <div className="flex h-full">
            {/* Chat Interface */}
            <div className="flex-1 border-r border-border/40">
                <ChatInterface />
            </div>

            {/* Query History Sidebar */}
            <div className="w-80 p-6 space-y-6 overflow-y-auto">
                {/* Quick Templates */}
                <div>
                    <div className="flex items-center gap-2 mb-3">
                        <Sparkles className="h-4 w-4 text-purple-400" />
                        <h3 className="text-sm font-semibold">Quick Templates</h3>
                    </div>
                    <div className="space-y-2">
                        {quickTemplates.map((template, idx) => (
                            <button
                                key={idx}
                                onClick={() => handleTemplateClick(template.query)}
                                className={`w-full p-2.5 text-left text-sm rounded-lg transition-all duration-200
                                    ${selectedTemplate === template.query
                                        ? 'bg-purple-500/20 border border-purple-500/50 text-purple-300'
                                        : 'bg-secondary/50 hover:bg-secondary border border-transparent hover:border-border/50'
                                    }`}
                            >
                                {template.label}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Query History */}
                <div>
                    <div className="flex items-center justify-between mb-3">
                        <div className="flex items-center gap-2">
                            <History className="h-4 w-4 text-muted-foreground" />
                            <h2 className="text-sm font-semibold">Recent Queries</h2>
                        </div>
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={fetchHistory}
                            disabled={loading}
                            className="h-7 w-7 p-0"
                        >
                            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
                        </Button>
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-6">
                            <Loader2 className="h-5 w-5 animate-spin text-purple-500" />
                        </div>
                    ) : queryHistory.length === 0 ? (
                        <div className="text-center py-6 text-muted-foreground text-xs">
                            No query history yet.<br />Send a message to get started!
                        </div>
                    ) : (
                        <div className="space-y-2 max-h-[calc(100vh-420px)] overflow-y-auto">
                            {queryHistory.slice(0, 10).map((item) => (
                                <Card
                                    key={item.id}
                                    className="p-2.5 bg-card/50 backdrop-blur-sm border-border/40 hover:border-primary/50 transition-colors cursor-pointer"
                                    onClick={() => handleTemplateClick(item.query)}
                                >
                                    <p className="text-xs font-medium line-clamp-2">{item.query}</p>
                                    <p className="text-[10px] text-muted-foreground mt-1">
                                        {getTimeAgo(item.timestamp)}
                                    </p>
                                </Card>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}
