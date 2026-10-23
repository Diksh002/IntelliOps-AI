const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchStats() {
    const res = await fetch(`${API_URL}/api/stats`);
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
}

export async function fetchDocuments() {
    const res = await fetch(`${API_URL}/api/documents`);
    if (!res.ok) throw new Error("Failed to fetch documents");
    return res.json();
}

export async function uploadDocument(file: File) {
    const formData = new FormData();
    formData.append("file", file);

    const res = await fetch(`${API_URL}/api/documents/upload`, {
        method: "POST",
        body: formData,
    });

    if (!res.ok) throw new Error("Failed to upload document");
    return res.json();
}

export async function fetchAgentActivity() {
    const res = await fetch(`${API_URL}/api/agents/activity`);
    if (!res.ok) throw new Error("Failed to fetch agent activity");
    return res.json();
}

export async function executeAgent(agentType: string, query: string) {
    const res = await fetch(`${API_URL}/api/agents/execute`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ agent_type: agentType, query }),
    });

    if (!res.ok) throw new Error("Failed to execute agent");
    return res.json();
}

export async function createCustomAgent(agent: {
    name: string;
    description: string;
    system_prompt: string;
    tools: string[];
}) {
    const res = await fetch(`${API_URL}/api/agents/custom`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify(agent),
    });

    if (!res.ok) throw new Error("Failed to create custom agent");
    return res.json();
}

export async function fetchCustomAgents() {
    const res = await fetch(`${API_URL}/api/agents/custom`);
    if (!res.ok) throw new Error("Failed to fetch custom agents");
    return res.json();
}

export async function deleteCustomAgent(agentId: number) {
    const res = await fetch(`${API_URL}/api/agents/custom/${agentId}`, {
        method: "DELETE",
    });

    if (!res.ok) throw new Error("Failed to delete custom agent");
    return res.json();
}

// ========== ANALYTICS API ==========

export interface AnalyticsSummary {
    total_queries: number;
    avg_latency_ms: number;
    recent_queries_24h: number;
    success_rate: number;
    queries_by_agent: Array<{ agent: string; count: number }>;
}

export async function fetchAnalyticsSummary(): Promise<AnalyticsSummary> {
    const res = await fetch(`${API_URL}/api/analytics/summary`);
    if (!res.ok) throw new Error("Failed to fetch analytics");
    return res.json();
}

// ========== SETTINGS API ==========

export interface UserSettings {
    openai_model: string;
    theme: string;
    notifications: string;
    auto_save: string;
}

export async function fetchSettings(): Promise<UserSettings> {
    const res = await fetch(`${API_URL}/api/settings`);
    if (!res.ok) throw new Error("Failed to fetch settings");
    return res.json();
}

export async function saveSettings(settings: Partial<UserSettings>): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_URL}/api/settings`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ settings }),
    });

    if (!res.ok) throw new Error("Failed to save settings");
    return res.json();
}

// ========== HISTORY API ==========

export interface QueryHistoryItem {
    id: number;
    query: string;
    result: string;
    timestamp: string;
}

export async function fetchQueryHistory(): Promise<QueryHistoryItem[]> {
    const res = await fetch(`${API_URL}/api/history`);
    if (!res.ok) throw new Error("Failed to fetch history");
    return res.json();
}

// ========== CHAT API ==========

export interface ChatResponse {
    response: string;
    thoughts: string[];
    data?: Record<string, unknown>;
    visual_artifact?: string;
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
    const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
        },
        body: JSON.stringify({ message }),
    });

    if (!res.ok) throw new Error("Failed to send message");
    return res.json();
}
