import React, { useState, useEffect } from 'react';
import { AlertTriangle, CheckCircle, AlertOctagon, ArrowRight } from 'lucide-react';

const InsightPanel = () => {
    const [insights, setInsights] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchInsights = async () => {
            try {
                const response = await fetch('http://localhost:8000/insights');
                if (!response.ok) throw new Error('Failed to fetch insights');
                const data = await response.json();
                setInsights(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchInsights();
    }, []);

    if (loading) return <div className="animate-pulse h-64 bg-zinc-100 dark:bg-zinc-800/50 rounded-xl"></div>;

    if (error) return (
        <div className="bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/50 p-4 rounded-xl text-red-600 dark:text-red-400 text-sm">
            Failed to load insights: {error}
        </div>
    );

    if (insights.length === 0) return (
        <div className="bg-white/80 dark:bg-zinc-900/50 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 p-6 rounded-xl shadow-sm text-center">
            <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-zinc-900 dark:text-white">All Systems Nominal</h3>
            <p className="text-zinc-500 dark:text-zinc-400 text-sm">No critical risks detected by the Autonomous Insight Engine.</p>
        </div>
    );

    // Map string severity to numeric score for display
    const severityToScore = (sev) => {
        if (sev === 'Critical') return 95;
        if (sev === 'High') return 80;
        if (sev === 'Medium') return 60;
        return 40;
    };

    const getSeverityColor = (score) => {
        if (score >= 90) return 'border-red-500 bg-red-50/50 dark:bg-red-900/10';
        if (score >= 70) return 'border-orange-500 bg-orange-50/50 dark:bg-orange-900/10';
        return 'border-yellow-500 bg-yellow-50/50 dark:bg-yellow-900/10';
    };

    const getSeverityIcon = (score) => {
        if (score >= 90) return <AlertOctagon className="w-5 h-5 text-red-500" />;
        return <AlertTriangle className="w-5 h-5 text-orange-500" />;
    };

    return (
        <div className="bg-white/80 dark:bg-zinc-900/50 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-xl hover:shadow-2xl transition-all">
            <div className="space-y-4">
                <div className="flex items-center justify-between">
                    <h2 className="text-xl font-bold text-zinc-900 dark:text-white tracking-tight flex items-center gap-2">
                        <div className="w-2 h-2 rounded-full bg-purple-500 animate-pulse"></div>
                        Autonomous Insight Engine
                    </h2>
                    <span className="text-xs font-mono bg-zinc-100 dark:bg-zinc-800 px-2 py-1 rounded text-zinc-500">
                        {insights.length} ISSUES DETECTED
                    </span>
                </div>

                <div className="grid grid-cols-1 gap-4">
                    {insights.map((insight, index) => {
                        const score = severityToScore(insight.severity);
                        return (
                            <div
                                key={index}
                                className={`border-l-4 p-4 rounded-r-xl shadow-sm hover:shadow-md transition-all bg-white dark:bg-zinc-900 ${getSeverityColor(score)} border-zinc-200 dark:border-zinc-800`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <div className="flex items-center gap-2">
                                        {getSeverityIcon(score)}
                                        <h3 className="font-bold text-zinc-900 dark:text-white text-base">
                                            {insight.issue}
                                        </h3>
                                    </div>
                                    <span className="text-xs font-bold font-mono px-2 py-1 rounded bg-white/50 dark:bg-black/20">
                                        SEVERITY: {insight.severity}
                                    </span>
                                </div>

                                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mt-3">
                                    <div>
                                        <p className="text-xs text-zinc-500 uppercase font-semibold mb-1">Severity Level</p>
                                        <p className="font-mono font-bold text-zinc-800 dark:text-zinc-200">
                                            {insight.severity}
                                        </p>
                                    </div>
                                    <div>
                                        <p className="text-xs text-zinc-500 uppercase font-semibold mb-1">Root Cause</p>
                                        <p className="font-bold text-zinc-800 dark:text-zinc-200">
                                            {insight.root_cause}
                                        </p>
                                    </div>
                                </div>

                                <div className="mt-4 pt-3 border-t border-zinc-100 dark:border-zinc-800/50">
                                    <p className="text-xs text-zinc-500 uppercase font-semibold mb-2">Recommended Actions</p>
                                    <div className="flex flex-wrap gap-2">
                                        {insight.recommended_action.map((action, i) => (
                                            <span key={i} className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-purple-50 dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 text-xs font-medium border border-purple-100 dark:border-purple-800/50">
                                                <ArrowRight size={12} />
                                                {action}
                                            </span>
                                        ))}
                                    </div>
                                </div>

                                <p className="mt-3 text-xs italic text-zinc-400">
                                    Impact: {insight.financial_impact}
                                </p>
                            </div>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

export default InsightPanel;
