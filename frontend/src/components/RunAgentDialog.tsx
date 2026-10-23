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
import { Textarea } from "@/components/ui/textarea";
import { Loader2, CheckCircle, XCircle } from "lucide-react";
import { useMutation } from "@tanstack/react-query";
import { executeAgent } from "@/lib/api";

interface RunAgentDialogProps {
    open: boolean;
    onOpenChange: (open: boolean) => void;
    agentName: string;
    agentType: string;
}

export function RunAgentDialog({ open, onOpenChange, agentName, agentType }: RunAgentDialogProps) {
    const [query, setQuery] = useState("");

    const executeMutation = useMutation({
        mutationFn: (query: string) => executeAgent(agentType, query),
        onSuccess: () => {
            // Keep dialog open to show results
        },
    });

    const handleExecute = () => {
        if (query.trim()) {
            executeMutation.mutate(query);
        }
    };

    const handleClose = () => {
        setQuery("");
        executeMutation.reset();
        onOpenChange(false);
    };

    return (
        <Dialog open={open} onOpenChange={handleClose}>
            <DialogContent className="sm:max-w-[600px]">
                <DialogHeader>
                    <DialogTitle>{agentName}</DialogTitle>
                    <DialogDescription>
                        What task would you like this agent to perform?
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-4 py-4">
                    <div className="space-y-2">
                        <label className="text-sm font-medium">Task Description</label>
                        <Textarea
                            placeholder="e.g., What was the total revenue from EMEA region in Q3?"
                            value={query}
                            onChange={(e) => setQuery(e.target.value)}
                            rows={4}
                            disabled={executeMutation.isPending || executeMutation.isSuccess}
                        />
                    </div>

                    {executeMutation.isPending && (
                        <div className="flex items-center gap-2 text-sm text-muted-foreground">
                            <Loader2 className="h-4 w-4 animate-spin" />
                            <span>Agent is processing your request...</span>
                        </div>
                    )}

                    {executeMutation.isSuccess && (
                        <div className="space-y-3">
                            <div className="flex items-center gap-2 text-sm text-green-500">
                                <CheckCircle className="h-4 w-4" />
                                <span>Completed in {executeMutation.data.duration_ms}ms</span>
                            </div>

                            <div className="rounded-lg border border-border bg-secondary/20 p-4">
                                <h4 className="font-semibold mb-2">Response:</h4>
                                <p className="text-sm whitespace-pre-wrap">{executeMutation.data.response}</p>
                            </div>
                        </div>
                    )}

                    {executeMutation.isError && (
                        <div className="flex items-center gap-2 text-sm text-red-500">
                            <XCircle className="h-4 w-4" />
                            <span>Error: {(executeMutation.error as Error).message}</span>
                        </div>
                    )}
                </div>

                <div className="flex justify-end gap-2">
                    <Button variant="outline" onClick={handleClose}>
                        Close
                    </Button>
                    {!executeMutation.isSuccess && (
                        <Button
                            onClick={handleExecute}
                            disabled={!query.trim() || executeMutation.isPending}
                        >
                            {executeMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                            Run Agent
                        </Button>
                    )}
                </div>
            </DialogContent>
        </Dialog>
    );
}
