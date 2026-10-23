"use client";

import {
    BarChart,
    Bar,
    LineChart,
    Line,
    PieChart,
    Pie,
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    Legend,
    ResponsiveContainer,
    Cell
} from "recharts";
import { Card } from "@/components/ui/card";

interface ChartConfig {
    type: "bar" | "line" | "pie" | "area";
    title: string;
    xAxisKey: string;
    dataKey: string;
    data: Record<string, unknown>[];
}

interface DynamicChartProps {
    config: ChartConfig;
}

const COLORS = [
    "#8b5cf6", // purple
    "#3b82f6", // blue
    "#10b981", // green
    "#f59e0b", // amber
    "#ef4444", // red
    "#ec4899", // pink
];

export function DynamicChart({ config }: DynamicChartProps) {
    const { type, title, xAxisKey, dataKey, data } = config;

    if (!data || data.length === 0) {
        return (
            <Card className="p-6 bg-card/50 border-border/50">
                <p className="text-sm text-muted-foreground">No data available for visualization</p>
            </Card>
        );
    }

    const renderChart = () => {
        switch (type) {
            case "bar":
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                            <XAxis
                                dataKey={xAxisKey}
                                stroke="#9ca3af"
                                tick={{ fill: '#9ca3af', fontSize: 12 }}
                            />
                            <YAxis
                                stroke="#9ca3af"
                                tick={{ fill: '#9ca3af', fontSize: 12 }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1f2937',
                                    border: '1px solid #374151',
                                    borderRadius: '8px',
                                    color: '#f3f4f6'
                                }}
                            />
                            <Legend wrapperStyle={{ color: '#9ca3af' }} />
                            <Bar dataKey={dataKey} fill="#8b5cf6" radius={[8, 8, 0, 0]} />
                        </BarChart>
                    </ResponsiveContainer>
                );

            case "line":
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <LineChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                            <XAxis
                                dataKey={xAxisKey}
                                stroke="#9ca3af"
                                tick={{ fill: '#9ca3af', fontSize: 12 }}
                            />
                            <YAxis
                                stroke="#9ca3af"
                                tick={{ fill: '#9ca3af', fontSize: 12 }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1f2937',
                                    border: '1px solid #374151',
                                    borderRadius: '8px',
                                    color: '#f3f4f6'
                                }}
                            />
                            <Legend wrapperStyle={{ color: '#9ca3af' }} />
                            <Line
                                type="monotone"
                                dataKey={dataKey}
                                stroke="#3b82f6"
                                strokeWidth={2}
                                dot={{ fill: '#3b82f6', r: 4 }}
                                activeDot={{ r: 6 }}
                            />
                        </LineChart>
                    </ResponsiveContainer>
                );

            case "pie":
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <PieChart>
                            <Pie
                                data={data}
                                dataKey={dataKey}
                                nameKey={xAxisKey}
                                cx="50%"
                                cy="50%"
                                outerRadius={100}
                                label={(entry: { name?: string | number; payload?: Record<string, unknown> }) =>
                                    String(entry.name ?? entry.payload?.[xAxisKey] ?? "")
                                }
                                labelLine={false}
                            >
                                {data.map((entry, index) => (
                                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                ))}
                            </Pie>
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1f2937',
                                    border: '1px solid #374151',
                                    borderRadius: '8px',
                                    color: '#f3f4f6'
                                }}
                            />
                            <Legend wrapperStyle={{ color: '#9ca3af' }} />
                        </PieChart>
                    </ResponsiveContainer>
                );

            case "area":
                return (
                    <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={data}>
                            <defs>
                                <linearGradient id="colorValue" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.8} />
                                    <stop offset="95%" stopColor="#10b981" stopOpacity={0.1} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.3} />
                            <XAxis
                                dataKey={xAxisKey}
                                stroke="#9ca3af"
                                tick={{ fill: '#9ca3af', fontSize: 12 }}
                            />
                            <YAxis
                                stroke="#9ca3af"
                                tick={{ fill: '#9ca3af', fontSize: 12 }}
                            />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: '#1f2937',
                                    border: '1px solid #374151',
                                    borderRadius: '8px',
                                    color: '#f3f4f6'
                                }}
                            />
                            <Legend wrapperStyle={{ color: '#9ca3af' }} />
                            <Area
                                type="monotone"
                                dataKey={dataKey}
                                stroke="#10b981"
                                fillOpacity={1}
                                fill="url(#colorValue)"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                );

            default:
                return <p className="text-sm text-muted-foreground">Unsupported chart type: {type}</p>;
        }
    };

    return (
        <Card className="p-6 bg-gradient-to-br from-card/80 to-card/40 border-border/50 backdrop-blur-sm">
            <h3 className="text-sm font-semibold mb-4 bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                {title}
            </h3>
            {renderChart()}
            <div className="mt-4 text-xs text-muted-foreground">
                <span className="inline-flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-purple-500"></span>
                    {data.length} data points
                </span>
            </div>
        </Card>
    );
}
