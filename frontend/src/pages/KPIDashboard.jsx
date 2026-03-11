import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import KpiCard from '../components/KpiCard';
import SkeletonCard from '../components/SkeletonCard';
import ExecutiveSummaryCard from '../components/ExecutiveSummaryCard';
import ForecastPanel from '../components/ForecastPanel';
import SimulationPanel from '../components/SimulationPanel';
import InsightPanel from '../components/InsightPanel';
import { RefreshCw, Activity, AlertTriangle } from 'lucide-react';

const KPIDashboard = () => {
    const [kpis, setKpis] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [lastRefreshed, setLastRefreshed] = useState(null);

    const fetchKpis = async () => {
        setLoading(true);
        try {
            const res = await fetch('http://localhost:8000/kpis');
            if (!res.ok) throw new Error('Failed to fetch KPIs');
            const data = await res.json();
            setKpis(data);
            setLastRefreshed(new Date());
            setError(null);
        } catch (err) {
            console.error(err);
            setError('Could not load KPI data. Ensure backend is running.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchKpis();
        const interval = setInterval(fetchKpis, 3600000); // Auto-refresh every 60 minutes
        return () => clearInterval(interval);
    }, []);

    // Extract Company Health
    const healthKpi = kpis.find(k => k.code === 'COMPANY_HEALTH');
    const otherKpis = kpis.filter(k => k.code !== 'COMPANY_HEALTH');

    // Categorization with section dividers
    const groups = {
        'Financial Health': ['NET_PROFIT_MARGIN', 'REVENUE_CONCENTRATION', 'SALARY_RATIO', 'REVENUE_PER_EMPLOYEE', 'BUDGET_OVERRUN'],
        'Operations': ['ON_TIME_DELIVERY', 'EMPLOYEE_UTILIZATION', 'ESCALATION_FREQUENCY'],
        'Client Success': ['AVG_CLIENT_RATING', 'CHURN_RISK_INDEX'],
    };

    const getGroup = (code) => {
        for (const [group, codes] of Object.entries(groups)) {
            if (codes.includes(code)) return group;
        }
        return 'Other Metrics';
    };

    // Group the data
    const groupedKpis = otherKpis.reduce((acc, kpi) => {
        const group = kpi.business_function || getGroup(kpi.code);
        if (!acc[group]) acc[group] = [];
        acc[group].push(kpi);
        return acc;
    }, {});

    return (
        <div className="p-4 md:p-8 overflow-y-auto h-full space-y-8 relative">
            {/* Header section */}
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
                <div>
                    <h1 className="text-2xl font-bold text-zinc-900 dark:text-white tracking-tight">Executive Dashboard</h1>
                    <p className="text-zinc-500 dark:text-zinc-500 text-sm mt-1">Real-time performance metrics and health monitoring.</p>
                </div>
                <button
                    onClick={fetchKpis}
                    disabled={loading}
                    className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 border border-zinc-200 dark:border-zinc-700 rounded-lg text-sm transition-all disabled:opacity-50 shadow-sm"
                >
                    <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                    {loading ? 'Refreshing...' : 'Refresh Data'}
                </button>
            </div>

            {error && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-500 p-4 rounded-xl flex items-center gap-3 relative z-10">
                    <AlertTriangle size={20} />
                    {error}
                </div>
            )}

            {/* PORTFOLIO MODE GRID */}
            <div className="grid grid-cols-1 gap-6 relative z-10">
                {/* 1. Executive Summary - High Level Narrative */}
                <ExecutiveSummaryCard />

                {/* 2. Strategy Layer - Forecast & Simulation */}
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2 space-y-6">
                        <ForecastPanel />
                        <InsightPanel />
                    </div>
                    <div className="lg:col-span-1">
                        <SimulationPanel />
                    </div>
                </div>
            </div>

            {/* KPI Grid with Section Dividers */}
            {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                    {[...Array(8)].map((_, i) => (
                        <SkeletonCard key={i} />
                    ))}
                </div>
            ) : (
                Object.entries(groupedKpis).map(([group, groupKpis], groupIndex) => (
                    <div key={group} className="space-y-6">
                        {/* Section Divider */}
                        <div className="flex items-center gap-4">
                            <div className="h-px bg-gradient-to-r from-zinc-200 via-zinc-300 dark:from-zinc-800 dark:via-zinc-700 to-transparent flex-1"></div>
                            <h3 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100 uppercase tracking-wider px-4">
                                {group}
                            </h3>
                            <div className="h-px bg-gradient-to-l from-zinc-200 via-zinc-300 dark:from-zinc-800 dark:via-zinc-700 to-transparent flex-1"></div>
                        </div>

                        {/* 12-column grid system */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
                            {groupKpis.map((kpi, index) => (
                                <KpiCard
                                    key={kpi.code}
                                    kpi={kpi}
                                    index={groupIndex * 10 + index}
                                />
                            ))}
                        </div>
                    </div>
                ))
            )}

            {!loading && kpis.length === 0 && !error && (
                <div className="text-center py-20 text-zinc-500">
                    No KPI data available.
                </div>
            )}
        </div>
    );
};

export default KPIDashboard;
