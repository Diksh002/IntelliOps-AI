"use client";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Upload, Search, Filter, Grid, List, FileText, CheckCircle, Clock, AlertCircle } from "lucide-react";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { fetchDocuments, uploadDocument } from "@/lib/api";
import { toast } from "sonner";

interface DocumentItem {
    id: string | number;
    name: string;
    status: string;
    size?: string;
    upload_date?: string;
}

export default function DocumentsPage() {
    const [viewMode, setViewMode] = useState<"grid" | "list">("grid");
    const queryClient = useQueryClient();

    const { data: documents } = useQuery<DocumentItem[]>({
        queryKey: ['documents'],
        queryFn: fetchDocuments,
        refetchInterval: 5000
    });

    const uploadMutation = useMutation({
        mutationFn: uploadDocument,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            toast.success("Document uploaded successfully");
        },
        onError: () => {
            toast.error("Failed to upload document");
        }
    });

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            uploadMutation.mutate(e.target.files[0]);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case "processed":
                return <CheckCircle className="h-4 w-4 text-green-500" />;
            case "processing":
                return <Clock className="h-4 w-4 text-yellow-500 animate-spin" />;
            case "failed":
                return <AlertCircle className="h-4 w-4 text-red-500" />;
            default:
                return <Clock className="h-4 w-4 text-gray-500" />;
        }
    };

    return (
        <div className="p-8 space-y-8">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-3xl font-bold">Document Intelligence Hub</h1>
                    <p className="text-muted-foreground">Manage and process your enterprise documents</p>
                </div>
                <div className="relative">
                    <input
                        type="file"
                        className="absolute inset-0 opacity-0 cursor-pointer"
                        onChange={handleFileUpload}
                        accept=".pdf"
                    />
                    <Button className="gap-2">
                        <Upload className="h-4 w-4" />
                        {uploadMutation.isPending ? "Uploading..." : "Upload Documents"}
                    </Button>
                </div>
            </div>

            {/* Search and Filters */}
            <Card className="p-4 bg-card/50 backdrop-blur-sm border-border/40">
                <div className="flex flex-wrap gap-4">
                    <div className="flex-1 min-w-[300px]">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                            <Input
                                placeholder="Search documents..."
                                className="pl-10"
                            />
                        </div>
                    </div>
                    <Button variant="outline" className="gap-2">
                        <Filter className="h-4 w-4" />
                        Filters
                    </Button>
                    <div className="flex gap-2">
                        <Button
                            variant={viewMode === "grid" ? "default" : "outline"}
                            size="icon"
                            onClick={() => setViewMode("grid")}
                        >
                            <Grid className="h-4 w-4" />
                        </Button>
                        <Button
                            variant={viewMode === "list" ? "default" : "outline"}
                            size="icon"
                            onClick={() => setViewMode("list")}
                        >
                            <List className="h-4 w-4" />
                        </Button>
                    </div>
                </div>
            </Card>

            {/* Documents Grid */}
            {viewMode === "grid" ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {documents?.map((doc: DocumentItem) => (
                        <Card key={doc.id} className="p-4 bg-card/50 backdrop-blur-sm border-border/40 hover:border-primary/50 transition-colors cursor-pointer">
                            <div className="flex items-start gap-3">
                                <div className="h-12 w-12 rounded-lg bg-blue-500/10 flex items-center justify-center flex-shrink-0">
                                    <FileText className="h-6 w-6 text-blue-500" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium truncate">{doc.name}</p>
                                    <div className="flex items-center gap-2 mt-1">
                                        {getStatusIcon(doc.status)}
                                        <span className="text-xs text-muted-foreground capitalize">{doc.status}</span>
                                    </div>
                                </div>
                            </div>
                            <div className="mt-4 pt-4 border-t border-border/20 flex items-center justify-between text-xs text-muted-foreground">
                                <span>{doc.size}</span>
                                <span>{doc.upload_date}</span>
                            </div>
                        </Card>
                    ))}
                </div>
            ) : (
                <Card className="p-4 bg-card/50 backdrop-blur-sm border-border/40">
                    <div className="space-y-2">
                        {documents?.map((doc: DocumentItem) => (
                            <div key={doc.id} className="flex items-center gap-4 p-3 rounded-lg hover:bg-secondary/50 cursor-pointer">
                                <FileText className="h-5 w-5 text-blue-500" />
                                <div className="flex-1 min-w-0">
                                    <p className="font-medium truncate">{doc.name}</p>
                                </div>
                                <div className="flex items-center gap-2">
                                    {getStatusIcon(doc.status)}
                                    <span className="text-xs text-muted-foreground capitalize w-20">{doc.status}</span>
                                </div>
                                <span className="text-xs text-muted-foreground w-16">{doc.size}</span>
                                <span className="text-xs text-muted-foreground w-24">{doc.upload_date}</span>
                            </div>
                        ))}
                    </div>
                </Card>
            )}
        </div>
    );
}
