"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Send, Bot, User, Loader2, BarChart3 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { DynamicChart } from "@/components/DynamicChart";
import ReactMarkdown from 'react-markdown';

interface ChartConfig {
  type: "bar" | "line" | "pie" | "area";
  title: string;
  xAxisKey: string;
  dataKey: string;
  data: Record<string, unknown>[];
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  thoughts?: string[];
  visualization?: ChartConfig;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMsg: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: input }),
      });

      if (!response.ok) throw new Error('Network response was not ok');

      const data = await response.json();

      // Parse visualization data if present
      let visualization: ChartConfig | undefined;
      if (data.visual_artifact) {
        try {
          visualization = typeof data.visual_artifact === 'string'
            ? JSON.parse(data.visual_artifact)
            : data.visual_artifact;
        } catch (e) {
          console.error("Failed to parse visualization:", e);
        }
      }

      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.response,
        thoughts: data.thoughts,
        visualization
      };
      setMessages(prev => [...prev, aiMsg]);

    } catch (error) {
      console.error("Error sending message:", error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "Sorry, I encountered an error connecting to the Agent Swarm. Please ensure the backend is running."
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-background/50 backdrop-blur-xl border-r border-border/40">
      <div className="p-4 border-b border-border/40 bg-background/80 backdrop-blur-md sticky top-0 z-10">
        <h2 className="text-lg font-semibold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
          DataScout AI
        </h2>
        <p className="text-xs text-muted-foreground">Enterprise Financial Intelligence</p>
      </div>

      <ScrollArea className="flex-1 p-4">
        <div className="space-y-6">
          {messages.map((msg) => (
            <motion.div
              key={msg.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${msg.role === "user" ? "bg-blue-500" : "bg-purple-500"
                }`}>
                {msg.role === "user" ? <User size={16} /> : <Bot size={16} />}
              </div>

              <div className={`flex flex-col gap-3 max-w-[85%] ${msg.role === "user" ? "items-end" : "items-start"}`}>
                <div className={`p-3 rounded-2xl ${msg.role === "user"
                  ? "bg-gradient-to-br from-blue-600 to-blue-500 text-white border border-blue-400/30 shadow-lg shadow-blue-500/20"
                  : "bg-card border border-border/50"
                  }`}>
                  {msg.role === "user" ? (
                    <p className="text-sm leading-relaxed">{msg.content}</p>
                  ) : (
                    <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none
                      prose-headings:text-foreground prose-headings:font-semibold prose-headings:mt-3 prose-headings:mb-2
                      prose-p:text-foreground prose-p:my-2
                      prose-li:text-foreground prose-li:my-1
                      prose-strong:text-foreground prose-strong:font-semibold
                      prose-code:text-purple-400 prose-code:bg-purple-950/30 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                      prose-pre:bg-secondary/50 prose-pre:border prose-pre:border-border/50
                      prose-ol:my-2 prose-ul:my-2
                      prose-ol:list-decimal prose-ul:list-disc
                      prose-li:marker:text-purple-400">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                </div>

                {msg.thoughts && (
                  <div className="text-xs text-muted-foreground space-y-1 pl-2 border-l-2 border-purple-500/30">
                    {msg.thoughts.map((thought, idx) => (
                      <div key={idx} className="flex items-center gap-2">
                        <Loader2 size={10} className="animate-spin" />
                        <span>{thought}</span>
                      </div>
                    ))}
                  </div>
                )}

                {msg.visualization && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.2 }}
                    className="w-full"
                  >
                    <div className="flex items-center gap-2 mb-2 text-xs text-muted-foreground">
                      <BarChart3 size={14} className="text-purple-400" />
                      <span>Data Visualization</span>
                    </div>
                    <DynamicChart config={msg.visualization} />
                  </motion.div>
                )}
              </div>
            </motion.div>
          ))}
          {isLoading && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-purple-500 flex items-center justify-center shrink-0">
                <Bot size={16} />
              </div>
              <div className="p-3 rounded-2xl bg-card border border-border/50">
                <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              </div>
            </motion.div>
          )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t border-border/40 bg-background/80 backdrop-blur-md">
        <div className="relative">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && !isLoading && sendMessage()}
            placeholder="Ask about revenue, trends, or reports..."
            className="pr-12 bg-secondary/50 border-border/50 focus-visible:ring-purple-500/50 text-foreground placeholder:text-muted-foreground/60"
            disabled={isLoading}
          />
          <Button
            size="icon"
            variant="ghost"
            className="absolute right-1 top-1 text-purple-400 hover:text-purple-300 hover:bg-purple-500/10"
            onClick={sendMessage}
            disabled={isLoading}
          >
            <Send size={18} />
          </Button>
        </div>
        <p className="text-xs text-muted-foreground mt-2 text-center">
          Try: &quot;Show me sales by region&quot; or &quot;What&apos;s in the ML assessment?&quot;
        </p>
      </div>
    </div>
  );
}
