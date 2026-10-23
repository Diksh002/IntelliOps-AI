"use client";

import { useState, useEffect, useCallback } from "react";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { User, Key, Bell, Shield, Save, Loader2 } from "lucide-react";
import { toast } from "sonner";

interface Settings {
    openai_model: string;
    theme: string;
    notifications: string;
    auto_save: string;
}

export default function SettingsPage() {
    const [settings, setSettings] = useState<Settings>({
        openai_model: "gpt-4o",
        theme: "dark",
        notifications: "true",
        auto_save: "true"
    });
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    const applyTheme = useCallback((theme: string) => {
        const root = document.documentElement;
        if (theme === 'dark') {
            root.classList.add('dark');
            root.classList.remove('light');
        } else if (theme === 'light') {
            root.classList.remove('dark');
            root.classList.add('light');
        } else if (theme === 'auto') {
            // Auto mode: check system preference
            const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
            if (prefersDark) {
                root.classList.add('dark');
                root.classList.remove('light');
            } else {
                root.classList.remove('dark');
                root.classList.add('light');
            }
        }
    }, []);

    const fetchSettings = useCallback(async () => {
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/settings`);
            if (!response.ok) throw new Error('Failed to fetch settings');
            const data = await response.json();
            setSettings(data);
            // Apply theme immediately after fetching
            applyTheme(data.theme);
        } catch (error) {
            console.error('Error fetching settings:', error);
            toast.error('Failed to load settings');
        } finally {
            setLoading(false);
        }
    }, [applyTheme]);

    useEffect(() => {
        fetchSettings();
    }, [fetchSettings]);

    const handleSave = async () => {
        setSaving(true);
        try {
            const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/settings`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ settings }),
            });

            if (!response.ok) throw new Error('Failed to save settings');

            // Apply theme immediately after saving
            applyTheme(settings.theme);

            toast.success('Settings saved successfully!');
        } catch (error) {
            console.error('Error saving settings:', error);
            toast.error('Failed to save settings');
        } finally {
            setSaving(false);
        }
    };

    const updateSetting = (key: keyof Settings, value: string) => {
        setSettings(prev => ({ ...prev, [key]: value }));
    };

    if (loading) {
        return (
            <div className="p-8 flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="h-12 w-12 animate-spin text-purple-500 mx-auto" />
                    <p className="mt-4 text-muted-foreground">Loading settings...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="p-8 space-y-8 max-w-4xl">
            <div>
                <h1 className="text-3xl font-bold">Settings</h1>
                <p className="text-muted-foreground">Manage your account and enterprise configuration</p>
            </div>

            {/* AI Model Configuration */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                <div className="flex items-center gap-3 mb-6">
                    <Key className="h-5 w-5 text-primary" />
                    <h2 className="text-lg font-semibold">AI Model Configuration</h2>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="text-sm font-medium mb-1.5 block">OpenAI Model</label>
                        <select
                            value={settings.openai_model}
                            onChange={(e) => updateSetting('openai_model', e.target.value)}
                            className="w-full p-2 bg-secondary border border-border rounded-md text-foreground"
                        >
                            <option value="gpt-4o">GPT-4o (Recommended)</option>
                            <option value="gpt-4-turbo">GPT-4 Turbo</option>
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                        </select>
                        <p className="text-xs text-muted-foreground mt-1">
                            Select the AI model for agent responses
                        </p>
                    </div>
                </div>
            </Card>

            {/* Appearance */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                <div className="flex items-center gap-3 mb-6">
                    <User className="h-5 w-5 text-primary" />
                    <h2 className="text-lg font-semibold">Appearance</h2>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="text-sm font-medium mb-1.5 block">Theme</label>
                        <select
                            value={settings.theme}
                            onChange={(e) => updateSetting('theme', e.target.value)}
                            className="w-full p-2 bg-secondary border border-border rounded-md text-foreground"
                        >
                            <option value="dark">Dark</option>
                            <option value="light">Light</option>
                            <option value="auto">Auto</option>
                        </select>
                    </div>
                </div>
            </Card>

            {/* Notifications */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                <div className="flex items-center gap-3 mb-6">
                    <Bell className="h-5 w-5 text-primary" />
                    <h2 className="text-lg font-semibold">Notifications</h2>
                </div>
                <div className="space-y-3">
                    <label className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg cursor-pointer hover:bg-secondary/30 transition-colors">
                        <span className="text-sm">Enable notifications</span>
                        <input
                            type="checkbox"
                            checked={settings.notifications === "true"}
                            onChange={(e) => updateSetting('notifications', e.target.checked ? "true" : "false")}
                            className="h-4 w-4"
                        />
                    </label>
                    <label className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg cursor-pointer hover:bg-secondary/30 transition-colors">
                        <span className="text-sm">Auto-save responses</span>
                        <input
                            type="checkbox"
                            checked={settings.auto_save === "true"}
                            onChange={(e) => updateSetting('auto_save', e.target.checked ? "true" : "false")}
                            className="h-4 w-4"
                        />
                    </label>
                </div>
            </Card>

            {/* Security */}
            <Card className="p-6 bg-card/50 backdrop-blur-sm border-border/40">
                <div className="flex items-center gap-3 mb-6">
                    <Shield className="h-5 w-5 text-primary" />
                    <h2 className="text-lg font-semibold">Security & Compliance</h2>
                </div>
                <div className="space-y-3">
                    <div className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg">
                        <span className="text-sm">Audit Logging</span>
                        <span className="text-xs text-green-500">Active</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg">
                        <span className="text-sm">Data Encryption</span>
                        <span className="text-xs text-green-500">Enabled</span>
                    </div>
                    <div className="flex items-center justify-between p-3 bg-secondary/20 rounded-lg">
                        <span className="text-sm">SOC 2 Compliance</span>
                        <span className="text-xs text-green-500">Certified</span>
                    </div>
                </div>
            </Card>

            <Button
                className="w-full gap-2"
                onClick={handleSave}
                disabled={saving}
            >
                {saving ? (
                    <>
                        <Loader2 className="h-4 w-4 animate-spin" />
                        Saving...
                    </>
                ) : (
                    <>
                        <Save className="h-4 w-4" />
                        Save Changes
                    </>
                )}
            </Button>
        </div>
    );
}
