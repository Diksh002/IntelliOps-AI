"use client";

import { Card } from "@/components/ui/card";
import { Bot, Zap, TrendingUp, CheckCircle, Play } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { fetchAgentActivity } from "@/lib/api";
import { RunAgentDialog } from "@/components/RunAgentDialog";
import { CreateAgentDialog } from "@/components/CreateAgentDialog";
import { useState } from "react";

const agentTemplates = [
    {
        name: "Financial Analyst",
        description: "Analyzes financial data, generates reports, and identifies trends",
        icon: TrendingUp,
        color: "blue",
        successRate: 94,
        avgTime: "2.3s",
        executions: 1284,
        type: "financial",
    },
    {
        name: "Compliance Officer",
        description: "Checks documents for regulatory compliance and risks",
        icon: CheckCircle,
        color: "green",
        successRate: 98,
        avgTime: "1.8s",
        executions: 892,
        type: "compliance",
    },
    {
        name: "Market Researcher",
        description: "Gathers market intelligence and competitive analysis",
        icon: Zap,
        color: "purple",
        successRate: 91,
        avgTime: "3.1s",
        executions: 567,
        type: "research",
    },
    {
        name: "SQL Expert",
        description: "Generates and optimizes complex SQL queries",
        icon: Bot,
        color: "orange",
        successRate: 96,
        avgTime: "1.2s",
        executions: 2103,
        type: "sql",
    },
];

interface ExecutionRecord {
    agent_name: string;
    query: string;
    duration_ms?: number;
    status?: string;
    timestamp?: string;
}

export default function AgentsPage() {
    const [runDialogOpen, setRunDialogOpen] = useState(false);
    const [createDialogOpen, setCreateDialogOpen] = useState(false);
    const [selectedAgent, setSelectedAgent] = useState<{ name: string; type: string } | null>(null);

    const { data: recentExecutions } = useQuery<ExecutionRecord[]>({
        queryKey: ['agentActivity'],
        queryFn: fetchAgentActivity,
        refetchInterval: 2000
    });

    const handleRunAgent = (name: string, type: string) => {
        setSelectedAgent({ name, type });
        setRunDialogOpen(true);
    };

    return (
        <div className="p-8 space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Agent Workbench</h1>
                    <p className="text-muted-foreground">Orchestrate your AI agent team</p>
                </div>
                <Button className="gap-2" onClick={() => setCreateDialogOpen(true)}>
                    <Play className="h-4 w-4" />
                    Create Custom Agent
                </Button>
            </div>

            {/* Agent Templates */}
            <div>
                <h2 className="text-xl font-semibold mb-4">Agent Templates</h2>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {agentTemplates.map((agent) => (
                        <Card key={agent.name} className="p-6 bg-card/50 backdrop-blur-sm border-border/40 hover:border-primary/50 transition-all">
                            <div className="flex items-start gap-4">
                                <div className={`h-12 w-12 rounded-lg bg-${agent.color}-500/10 flex items-center justify-center flex-shrink-0`}>
                                    <agent.icon className={`h-6 w-6 text-${agent.color}-500`} />
                                </div>
                                <div className="flex-1">
                                    <h3 className="font-semibold text-lg">{agent.name}</h3>
                                    <p className="text-sm text-muted-foreground mt-1">{agent.description}</p>

                                    <div className="grid grid-cols-3 gap-4 mt-4">
                                        <div>
                                            <p className="text-xs text-muted-foreground">Success Rate</p>
                                            <p className="text-lg font-bold text-green-500">{agent.successRate}%</p>
                                        </div>
                                        <div>
                                            <p className="text-xs text-muted-foreground">Avg Time</p>
                                            <p className="text-lg font-bold">{agent.avgTime}</p>
                                        </div>
                                        <div>
                                            <p className="text-xs text-muted-foreground">Executions</p>
                                            <p className="text-lg font-bold">{agent.executions.toLocaleString()}</p>
                                        </div>
                                    </div>

                                    <Button
                                        className="w-full mt-4"
                                        variant="outline"
                                        onClick={() => handleRunAgent(agent.name, agent.type)}
                                    >
                                        <Play className="h-4 w-4 mr-2" />
                                        Run Agent
                                    </Button>
                                </div>
                            </div>
                        </Card>
                    ))}
                </div>
            </div>

            {/* Recent Executions */}
            <div>
                <h2 className="text-xl font-semibold mb-4">Recent Executions</h2>
                <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                    <div className="space-y-4">
                        {recentExecutions?.map((execution: ExecutionRecord, index: number) => (
                            <div key={index} className="flex items-center gap-4 p-3 rounded-lg bg-secondary/20">
                                <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                                    <Bot className="h-5 w-5 text-white" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium">{execution.agent_name}</p>
                                    <p className="text-sm text-muted-foreground truncate">{execution.query}</p>
                                </div>
                                <div className="flex items-center gap-3">
                                    <div className="flex items-center gap-2">
                                        <CheckCircle className="h-4 w-4 text-green-500" />
                                        <span className="text-sm text-green-500">Completed</span>
                                    </div>
                                    <span className="text-sm text-muted-foreground w-16 text-right">{execution.duration_ms}ms</span>
                                </div>
                            </div>
                        ))}
                        {!recentExecutions?.length && (
                            <div className="text-center text-muted-foreground py-4">No recent activity</div>
                        )}
                    </div>
                </Card>
            </div>

            {/* Performance Overview */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                    <h3 className="font-semibold mb-2">Total Executions</h3>
                    <p className="text-3xl font-bold">4,846</p>
                    <p className="text-sm text-green-500 mt-1">+18.2% from last week</p>
                </Card>
                <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                    <h3 className="font-semibold mb-2">Average Success Rate</h3>
                    <p className="text-3xl font-bold">94.8%</p>
                    <p className="text-sm text-green-500 mt-1">+2.1% improvement</p>
                </Card>
                <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                    <h3 className="font-semibold mb-2">Avg Response Time</h3>
                    <p className="text-3xl font-bold">2.1s</p>
                    <p className="text-sm text-green-500 mt-1">-0.3s faster</p>
                </Card>
            </div>

            {/* Dialogs */}
            {selectedAgent && (
                <RunAgentDialog
                    open={runDialogOpen}
                    onOpenChange={setRunDialogOpen}
                    agentName={selectedAgent.name}
                    agentType={selectedAgent.type}
                />
            )}

            <CreateAgentDialog
                open={createDialogOpen}
                onOpenChange={setCreateDialogOpen}
            />
        </div>
    );
}
