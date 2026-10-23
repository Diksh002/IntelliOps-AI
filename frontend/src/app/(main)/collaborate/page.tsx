"use client";

import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Users, Plus, MessageCircle, FileText } from "lucide-react";
import { toast } from "sonner";

const workspaces = [
    { name: "Q4 Financial Review", members: 5, queries: 23, documents: 12, lastActive: "2m ago" },
    { name: "Market Research 2024", members: 3, queries: 15, documents: 8, lastActive: "15m ago" },
    { name: "Compliance Audit", members: 4, queries: 31, documents: 24, lastActive: "1h ago" },
];

export default function CollaboratePage() {
    return (
        <div className="p-8 space-y-8">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Collaboration Spaces</h1>
                    <p className="text-muted-foreground">Work together on insights and analysis</p>
                </div>
                <Button className="gap-2" onClick={() => toast.info("New Workspace wizard coming soon")}>
                    <Plus className="h-4 w-4" />
                    New Workspace
                </Button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {workspaces.map((workspace) => (
                    <Card key={workspace.name} className="p-6 bg-card/50 backdrop-blur-sm border-border/40 hover:border-primary/50 transition-all cursor-pointer">
                        <div className="flex items-start justify-between mb-4">
                            <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center">
                                <Users className="h-6 w-6 text-blue-500" />
                            </div>
                            <span className="text-xs text-muted-foreground">{workspace.lastActive}</span>
                        </div>
                        <h3 className="font-semibold text-lg mb-2">{workspace.name}</h3>
                        <div className="grid grid-cols-3 gap-2 text-sm">
                            <div>
                                <p className="text-muted-foreground text-xs">Members</p>
                                <p className="font-medium">{workspace.members}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs">Queries</p>
                                <p className="font-medium">{workspace.queries}</p>
                            </div>
                            <div>
                                <p className="text-muted-foreground text-xs">Docs</p>
                                <p className="font-medium">{workspace.documents}</p>
                            </div>
                        </div>
                        <div className="flex gap-2 mt-4 pt-4 border-t border-border/20">
                            <Button size="sm" variant="outline" className="flex-1 text-xs" onClick={() => toast.info(`Opening chat for ${workspace.name}...`)}>
                                <MessageCircle className="h-3 w-3 mr-1" />
                                Chat
                            </Button>
                            <Button size="sm" variant="outline" className="flex-1 text-xs" onClick={() => toast.info(`Accessing files for ${workspace.name}...`)}>
                                <FileText className="h-3 w-3 mr-1" />
                                Files
                            </Button>
                        </div>
                    </Card>
                ))}
            </div>
        </div>
    );
}
