
import React, { useEffect, useState } from 'react';
import { Sparkles, TrendingUp, AlertTriangle, Lightbulb } from 'lucide-react';

const ExecutiveSummaryCard = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const response = await fetch('http://127.0.0.1:8000/summary');
                if (!response.ok) throw new Error('Failed to fetch summary');
                const result = await response.json();
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchSummary();
    }, []);

    if (loading) return <div className="animate-pulse h-48 bg-zinc-100 dark:bg-zinc-800/50 rounded-xl"></div>;
    if (error) return <div className="text-red-500 p-4 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-900/50">Error: {error}</div>;

    return (
        <div className="bg-white/80 dark:bg-zinc-900/50 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-xl relative overflow-hidden transition-all hover:shadow-2xl">
            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                <Sparkles size={100} className="text-zinc-900 dark:text-white" />
            </div>

            <h2 className="text-xl font-bold text-zinc-900 dark:text-white mb-6 flex items-center gap-2 tracking-tight">
                <Sparkles className="text-yellow-500 fill-yellow-500" />
                Executive Summary
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

                {/* Financial */}
                <div className="p-4 bg-zinc-50/50 dark:bg-zinc-800/50 rounded-lg border-l-4 border-green-500 backdrop-blur-sm">
                    <h3 className="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2 flex items-center gap-2 font-semibold">
                        <TrendingUp size={14} /> Financial Health
                    </h3>
                    <p className="text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed">{data.financial_health}</p>
                </div>

                {/* Operational */}
                <div className="p-4 bg-zinc-50/50 dark:bg-zinc-800/50 rounded-lg border-l-4 border-blue-500 backdrop-blur-sm">
                    <h3 className="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2 flex items-center gap-2 font-semibold">
                        <ActivityIcon /> Operational Strain
                    </h3>
                    <p className="text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed">{data.operational_strain}</p>
                </div>

                {/* Client Risk */}
                <div className="p-4 bg-zinc-50/50 dark:bg-zinc-800/50 rounded-lg border-l-4 border-orange-500 backdrop-blur-sm">
                    <h3 className="text-xs uppercase tracking-wider text-zinc-500 dark:text-zinc-400 mb-2 flex items-center gap-2 font-semibold">
                        <AlertTriangle size={14} /> Client Risk
                    </h3>
                    <p className="text-zinc-800 dark:text-zinc-200 font-medium leading-relaxed">{data.client_risk}</p>
                </div>

                {/* Action Item */}
                <div className="p-4 bg-indigo-50/50 dark:bg-indigo-900/20 rounded-lg border-l-4 border-indigo-500 col-span-1 md:col-span-2 backdrop-blur-sm">
                    <h3 className="text-xs uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-2 flex items-center gap-2 font-semibold">
                        <Lightbulb size={14} /> Recommended Action
                    </h3>
                    <p className="text-zinc-900 dark:text-white text-lg font-bold">{data.immediate_action}</p>
                </div>

            </div>
        </div>
    );
};

// Simple Icon for Activity
const ActivityIcon = () => (
    <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
    >
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
);

export default ExecutiveSummaryCard;
