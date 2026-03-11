
import React, { useEffect, useState } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { TrendingUp, Activity, AlertCircle } from 'lucide-react';

const ForecastPanel = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchForecast = async () => {
            try {
                const response = await fetch('http://127.0.0.1:8000/forecast');
                if (!response.ok) throw new Error('Failed to fetch forecast');
                const result = await response.json();
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchForecast();
    }, []);

    if (loading) return <div className="animate-pulse h-96 bg-zinc-100 dark:bg-zinc-800/50 rounded-xl"></div>;
    if (error) return <div className="text-red-500 p-4 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-900/50">Error: {error}</div>;

    const { forecast, summary } = data;

    return (
        <div className="bg-white/80 dark:bg-zinc-900/50 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-xl flex flex-col hover:shadow-2xl transition-all">
            <div className="flex justify-between items-start mb-6">
                <div>
                    <h2 className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-2 tracking-tight">
                        <TrendingUp className="text-blue-500" />
                        3-Month Financial Projection
                    </h2>
                    <p className="text-zinc-500 dark:text-zinc-400 text-sm mt-1">Based on linear regression of past 12 months</p>
                </div>

                <div className={`px-4 py-2 rounded-lg border ${summary.risk_level === 'SAFE' ? 'bg-green-500/10 border-green-500/20 text-green-600 dark:text-green-400' :
                    summary.risk_level === 'WARNING' ? 'bg-yellow-500/10 border-yellow-500/20 text-yellow-600 dark:text-yellow-400' :
                        'bg-red-500/10 border-red-500/20 text-red-600 dark:text-red-400'
                    }`}>
                    <div className="text-[10px] uppercase tracking-wider font-bold opacity-80">Runway</div>
                    <div className="text-xl font-mono font-bold">
                        {summary.runway_months > 99 ? '>12' : summary.runway_months} Months
                    </div>
                </div>
            </div>

            <div className="h-64 w-full flex-grow min-h-[250px]">
                <ResponsiveContainer width="99%" height="100%">
                    <LineChart data={forecast}>
                        <CartesianGrid strokeDasharray="3 3" stroke="currentColor" className="text-zinc-200 dark:text-zinc-800" />
                        <XAxis
                            dataKey="month"
                            stroke="currentColor"
                            className="text-zinc-400 text-xs font-medium"
                            tick={{ fill: 'currentColor' }}
                        />
                        <YAxis
                            stroke="currentColor"
                            className="text-zinc-400 text-xs font-medium"
                            tick={{ fill: 'currentColor' }}
                        />
                        <YAxis
                            yAxisId="right"
                            orientation="right"
                            stroke="currentColor"
                            className="text-zinc-400 text-xs font-medium"
                            tick={{ fill: 'currentColor' }}
                        />
                        <Tooltip
                            contentStyle={{
                                backgroundColor: '#18181b',
                                borderColor: '#27272a',
                                color: '#f4f4f5',
                                borderRadius: '0.5rem',
                                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                            }}
                            itemStyle={{ color: '#e4e4e7' }}
                            formatter={(value, name) => [
                                name === 'Margin %' ? `${value.toFixed(1)}%` : `₹${value.toLocaleString()}`,
                                name
                            ]}
                        />
                        <Legend />
                        <Line type="monotone" dataKey="revenue" name="Revenue" stroke="#3b82f6" strokeWidth={3} dot={{ r: 4, strokeWidth: 2 }} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey="expenses" name="Expenses" stroke="#ef4444" strokeWidth={2} dot={{ r: 4 }} />
                        <Line yAxisId="right" type="monotone" dataKey="net_margin" name="Margin %" stroke="#10b981" strokeDasharray="5 5" strokeWidth={2} dot={false} />
                    </LineChart>
                </ResponsiveContainer>
            </div>

            <div className="mt-6 flex flex-wrap gap-4 text-sm">
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-700/50">
                    <Activity size={16} className="text-zinc-400" />
                    <span className="text-zinc-500 dark:text-zinc-400">Trend:</span>
                    <span className={summary.trend_revenue === 'UP' ? 'text-green-500 font-bold' : 'text-red-500 font-bold'}>{summary.trend_revenue}</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-700/50">
                    <AlertCircle size={16} className="text-zinc-400" />
                    <span className="text-zinc-500 dark:text-zinc-400">Est. Cash:</span>
                    <span className="text-zinc-900 dark:text-white font-mono font-bold">₹{summary.estimated_cash_on_hand.toLocaleString()}</span>
                </div>
            </div>
        </div>
    );
};

export default ForecastPanel;
