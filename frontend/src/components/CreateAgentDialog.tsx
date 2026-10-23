"use client";

import { useState } from "react";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createCustomAgent } from "@/lib/api";
import { toast } from "sonner";

interface CreateAgentDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export function CreateAgentDialog({ open, onOpenChange }: CreateAgentDialogProps) {
    const [name, setName] = useState("");
    const [description, setDescription] = useState("");
    const [systemPrompt, setSystemPrompt] = useState("");
    const [tools, setTools] = useState<string[]>([]);

    const queryClient = useQueryClient();

    const createMutation = useMutation({
        mutationFn: createCustomAgent,
        onSuccess: () => {
            toast.success("Custom agent created successfully!");
            queryClient.invalidateQueries({ queryKey: ['customAgents'] });
            handleClose();
        },
        onError: (error: Error) => {
            toast.error(`Failed to create agent: ${error.message}`);
        },
    });

    const handleClose = () => {
        setName("");
        setDescription("");
        setSystemPrompt("");
        setTools([]);
        onOpenChange(false);
    };

    const handleToolToggle = (tool: string) => {
        setTools(prev =>
            prev.includes(tool)
                ? prev.filter(t => t !== tool)
                : [...prev, tool]
        );
    };

    const handleCreate = () => {
        if (!name.trim() || !systemPrompt.trim() || tools.length === 0) {
            toast.error("Please fill in all required fields");
            return;
        }

        createMutation.mutate({
            name,
            description,
            system_prompt: systemPrompt,
            tools,
        });
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
                <DialogHeader>
                    <DialogTitle>Create Custom Agent</DialogTitle>
                    <DialogDescription>
                        Build a specialized AI agent tailored to your business needs
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <Label htmlFor="name">Agent Name *</Label>
                        <Input
                            id="name"
                            placeholder="e.g., Payroll Auditor"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="description">Description</Label>
                        <Input
                            id="description"
                            placeholder="Brief description of what this agent does"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                        />
                    </div>

                    <div className="space-y-2">
                        <Label htmlFor="prompt">System Prompt *</Label>
                        <Textarea
                            id="prompt"
                            placeholder="e.g., You are an expert financial auditor specializing in detecting anomalies in payroll data. Always provide specific examples and cite data sources."
                            value={systemPrompt}
                            onChange={(e) => setSystemPrompt(e.target.value)}
                            rows={5}
                        />
                        <p className="text-xs text-muted-foreground">
                            Define the agent&apos;s expertise, tone, and behavior
                        </p>
                    </div>

                    <div className="space-y-2">
                        <Label>Available Tools *</Label>
                        <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                                <Checkbox
                                    id="sql"
                                    checked={tools.includes("sql")}
                                    onCheckedChange={() => handleToolToggle("sql")}
                                />
                                <label
                                    htmlFor="sql"
                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                >
                                    SQL Database Access
                                </label>
                            </div>
                            <p className="text-xs text-muted-foreground ml-6">
                                Query financial transactions, payroll, and other structured data
                            </p>

                            <div className="flex items-center space-x-2">
                                <Checkbox
                                    id="rag"
                                    checked={tools.includes("rag")}
                                    onCheckedChange={() => handleToolToggle("rag")}
                                />
                                <label
                                    htmlFor="rag"
                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                >
                                    Document Search
                                </label>
                            </div>
                            <p className="text-xs text-muted-foreground ml-6">
                                Search and analyze uploaded reports and documents
                            </p>
                        </div>
                    </div>
                </div>

                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={handleClose}>
                        Cancel
                    </Button>
                    <Button
                        onClick={handleCreate}
                        disabled={createMutation.isPending}
                    >
                        {createMutation.isPending ? "Creating..." : "Create Agent"}
                    </Button>
                </div>
            </DialogContent>
        </Dialog>
    );
}
