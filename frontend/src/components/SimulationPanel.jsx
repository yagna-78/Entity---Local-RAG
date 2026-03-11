
import React, { useState } from 'react';
import { Play, RotateCcw, ArrowRight, TrendingUp, TrendingDown, Users, DollarSign } from 'lucide-react';

const SimulationPanel = () => {
    const [params, setParams] = useState({
        revenue_pct_change: 0,
        salary_pct_change: 0,
        new_employees: 0,
        salary_per_hire: 0, // Enforced input for new hires
        marketing_spend_increase: 0,
        clients_removed: [] // Logic for clients list selection is complex, omitting for Phase 1 UI simplicity
    });

    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setParams(prev => ({ ...prev, [name]: parseFloat(value) || 0 }));
    };

    const runSimulation = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch('http://127.0.0.1:8000/simulate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params),
            });
            if (!response.ok) throw new Error('Simulation failed');
            const data = await response.json();
            setResult(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const reset = () => {
        setParams({
            revenue_pct_change: 0,
            salary_pct_change: 0,
            new_employees: 0,
            salary_per_hire: 0,
            marketing_spend_increase: 0,
            clients_removed: []
        });
        setResult(null);
    };

    return (
        <div className="bg-white/80 dark:bg-zinc-900/50 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 p-6 rounded-xl shadow-xl hover:shadow-2xl transition-all h-full flex flex-col">
            <h2 className="text-xl font-bold text-zinc-900 dark:text-white mb-6 flex items-center gap-2 tracking-tight flex-shrink-0">
                <Play className="text-purple-500 fill-purple-500" />
                Scenario Simulator <span className="text-xs font-normal text-zinc-500 bg-zinc-100 dark:bg-zinc-800 px-2 py-0.5 rounded-full border border-zinc-200 dark:border-zinc-700 ml-2">In-Memory</span>
            </h2>

            {/* Inputs - flex-1 ensures it pushes controls downward if needed */}
            <div className="grid grid-cols-1 md:grid-cols-1 xl:grid-cols-2 gap-4 mb-6 flex-1">
                <div>
                    <label className="block text-zinc-500 dark:text-zinc-400 text-xs uppercase font-semibold mb-1.5 ml-1">Revenue Change (%)</label>
                    <input
                        type="number" name="revenue_pct_change"
                        value={params.revenue_pct_change} onChange={handleChange}
                        className="w-full bg-zinc-50 dark:bg-zinc-950/50 text-zinc-900 dark:text-white border border-zinc-200 dark:border-zinc-700 rounded-lg p-2.5 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all placeholder-zinc-400"
                    />
                </div>
                <div>
                    <label className="block text-zinc-500 dark:text-zinc-400 text-xs uppercase font-semibold mb-1.5 ml-1">Salary Change (%)</label>
                    <input
                        type="number" name="salary_pct_change"
                        value={params.salary_pct_change} onChange={handleChange}
                        className="w-full bg-zinc-50 dark:bg-zinc-950/50 text-zinc-900 dark:text-white border border-zinc-200 dark:border-zinc-700 rounded-lg p-2.5 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all placeholder-zinc-400"
                    />
                </div>
                <div>
                    <label className="block text-zinc-500 dark:text-zinc-400 text-xs uppercase font-semibold mb-1.5 ml-1">New Hires</label>
                    <input
                        type="number" name="new_employees"
                        value={params.new_employees} onChange={handleChange}
                        className="w-full bg-zinc-50 dark:bg-zinc-950/50 text-zinc-900 dark:text-white border border-zinc-200 dark:border-zinc-700 rounded-lg p-2.5 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all placeholder-zinc-400"
                    />
                </div>

                {/* Conditional Salary Input */}
                {params.new_employees > 0 && (
                    <div className="animate-fadeIn">
                        <label className="block text-zinc-500 dark:text-zinc-400 text-xs uppercase font-semibold mb-1.5 ml-1">
                            Salary per Hire (₹) <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="number" name="salary_per_hire"
                            value={params.salary_per_hire} onChange={handleChange}
                            placeholder="e.g. 50000"
                            className={`w-full bg-zinc-50 dark:bg-zinc-950/50 text-zinc-900 dark:text-white border rounded-lg p-2.5 outline-none transition-all placeholder-zinc-400 ${params.salary_per_hire <= 0 ? 'border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500' : 'border-zinc-200 dark:border-zinc-700 focus:border-purple-500 focus:ring-1 focus:ring-purple-500'
                                }`}
                        />
                        {params.salary_per_hire <= 0 && (
                            <div className="text-[10px] text-red-500 mt-1">Required for simulation</div>
                        )}
                    </div>
                )}
                <div>
                    <label className="block text-zinc-500 dark:text-zinc-400 text-xs uppercase font-semibold mb-1.5 ml-1">Marketing Spend (+₹)</label>
                    <input
                        type="number" name="marketing_spend_increase"
                        value={params.marketing_spend_increase} onChange={handleChange}
                        className="w-full bg-zinc-50 dark:bg-zinc-950/50 text-zinc-900 dark:text-white border border-zinc-200 dark:border-zinc-700 rounded-lg p-2.5 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 outline-none transition-all placeholder-zinc-400"
                    />
                </div>
            </div>

            {/* Controls */}
            <div className="flex gap-4 mb-8 border-b border-zinc-200 dark:border-zinc-800 pb-8 items-center">
                <button
                    onClick={runSimulation}
                    disabled={loading || (params.new_employees > 0 && params.salary_per_hire <= 0)}
                    className="bg-purple-600 hover:bg-purple-700 disabled:bg-zinc-300 disabled:dark:bg-zinc-800 disabled:text-zinc-500 text-white px-6 py-2.5 rounded-lg font-bold flex items-center gap-2 transition-all disabled:opacity-50 shadow-lg shadow-purple-500/20 active:scale-95"
                >
                    {loading ? 'Simulating...' : 'Run Simulation'}
                    {!loading && <Play size={16} fill="currentColor" />}
                </button>
                <button
                    onClick={reset}
                    className="bg-zinc-100 hover:bg-zinc-200 dark:bg-zinc-800 dark:hover:bg-zinc-700 text-zinc-600 dark:text-zinc-300 px-4 py-2.5 rounded-lg font-medium flex items-center gap-2 transition-all active:scale-95"
                >
                    <RotateCcw size={16} /> Reset
                </button>
            </div>

            {error && <div className="text-red-500 mb-4 bg-red-50 dark:bg-red-900/10 p-3 rounded-lg border border-red-200 dark:border-red-900/50">Error: {error}</div>}

            {/* Results Display */}
            {result && result.baseline && result.simulated && (
                <div className="grid grid-cols-1 gap-6 animate-fadeIn mt-6">
                    {/* Revenue Card */}
                    <MetricCard
                        title="Revenue"
                        baseline={result.baseline.revenue ?? 0}
                        simulated={result.simulated.revenue ?? 0}
                        icon={<DollarSign size={20} className="text-green-500" />}
                        formatCurrency
                    />

                    {/* Margin Card */}
                    <MetricCard
                        title="Net Margin"
                        baseline={result.baseline.net_margin ?? result.baseline.margin ?? 0}
                        simulated={result.simulated.net_margin ?? result.simulated.margin ?? 0}
                        icon={<TrendingUp size={20} className="text-blue-500" />}
                        suffix="%"
                    />

                    {/* Employees Card */}
                    <MetricCard
                        title="Employees"
                        baseline={result.baseline.employees ?? result.baseline.employee_count ?? 0}
                        simulated={result.simulated.employees ?? result.simulated.employee_count ?? 0}
                        icon={<Users size={20} className="text-orange-500" />}
                    />
                </div>
            )}
        </div>
    );
};

const MetricCard = ({ title, baseline, simulated, icon, formatCurrency, suffix = '' }) => {
    const diff = simulated - baseline;
    const pct = baseline !== 0 ? ((diff / baseline) * 100).toFixed(1) : 0;
    const isPositive = diff >= 0;

    const format = (val) => {
        if (formatCurrency) return `₹${val.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
        return `${val.toLocaleString(undefined, { maximumFractionDigits: 1 })}${suffix}`;
    };

    return (
        <div className="bg-zinc-50/50 dark:bg-zinc-950/30 p-5 rounded-xl border border-zinc-200 dark:border-zinc-800 relative overflow-hidden group hover:border-purple-500/30 transition-all">
            <div className="flex justify-between items-start mb-3">
                <span className="text-zinc-500 dark:text-zinc-400 text-sm font-semibold flex items-center gap-2">
                    {icon} {title}
                </span>
                <span className={`text-[10px] font-bold px-2 py-1 rounded-full border ${isPositive ? 'bg-green-500/10 text-green-600 dark:text-green-400 border-green-500/20' : 'bg-red-500/10 text-red-600 dark:text-red-400 border-red-500/20'}`}>
                    {isPositive ? '+' : ''}{pct}%
                </span>
            </div>

            <div className="flex items-end gap-3 justify-between">
                <div>
                    <div className="text-[10px] text-zinc-400 dark:text-zinc-500 mb-1 font-bold tracking-wider">BASELINE</div>
                    <div className="text-lg font-mono text-zinc-400 line-through decoration-zinc-400/50">
                        {format(baseline)}
                    </div>
                </div>
                <ArrowRight className="text-zinc-300 dark:text-zinc-600 mb-2" size={20} />
                <div className="text-right">
                    <div className="text-[10px] text-purple-600 dark:text-purple-400 mb-1 font-bold tracking-wider">SIMULATED</div>
                    <div className="text-2xl font-mono font-bold text-zinc-900 dark:text-white">
                        {format(simulated)}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default SimulationPanel;
