
import React, { useEffect, useState } from 'react';
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer } from 'recharts';
import { AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';

const RiskRadar = () => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchRisk = async () => {
            try {
                const response = await fetch('http://127.0.0.1:8000/risk');
                if (!response.ok) throw new Error('Failed to fetch risk profile');
                const result = await response.json();
                setData(result);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        };

        fetchRisk();
    }, []);

    if (loading) return <div className="animate-pulse h-64 bg-zinc-100 dark:bg-zinc-800/50 rounded-xl"></div>;
    if (error) return <div className="text-red-500 p-4 bg-red-50 dark:bg-red-900/10 rounded-xl border border-red-200 dark:border-red-900/50">Error: {error}</div>;

    const chartData = [
        { subject: 'Financial', A: data.breakdown.financial_risk, fullMark: 100 },
        { subject: 'Operational', A: data.breakdown.operational_risk, fullMark: 100 },
        { subject: 'Client', A: data.breakdown.client_risk, fullMark: 100 },
    ];

    const getStatusColor = (status) => {
        if (status === 'CRITICAL') return 'text-red-500';
        if (status === 'AT RISK') return 'text-yellow-500';
        return 'text-green-500';
    };

    const StatusIcon = ({ status }) => {
        if (status === 'CRITICAL') return <ShieldAlert className="w-6 h-6 text-red-500" />;
        if (status === 'AT RISK') return <AlertTriangle className="w-6 h-6 text-yellow-500" />;
        return <CheckCircle className="w-6 h-6 text-green-500" />;
    };

    return (
        <div className="bg-white/80 dark:bg-zinc-900/50 backdrop-blur-md border border-zinc-200 dark:border-zinc-800 rounded-xl p-6 shadow-xl flex flex-col justify-between h-full hover:shadow-2xl transition-all">
            <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-zinc-900 dark:text-white flex items-center gap-2 tracking-tight">
                    <StatusIcon status={data.status} />
                    Risk Radar
                </h2>
                <span className={`font-mono font-bold ${getStatusColor(data.status)}`}>
                    {data.status} ({data.overall_score}/100)
                </span>
            </div>

            <div className="h-64 w-full flex-grow min-h-[250px]">
                <ResponsiveContainer width="99%" height="100%">
                    <RadarChart cx="50%" cy="50%" outerRadius="70%" data={chartData}>
                        <PolarGrid stroke="currentColor" className="text-zinc-200 dark:text-zinc-700" />
                        <PolarAngleAxis
                            dataKey="subject"
                            tick={{ fill: 'currentColor', fontSize: 12, className: "text-zinc-500 dark:text-zinc-400 font-medium" }}
                        />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
                        <Radar
                            name="Risk Level"
                            dataKey="A"
                            stroke="#8b5cf6"
                            strokeWidth={3}
                            fill="#8b5cf6"
                            fillOpacity={0.3}
                        />
                    </RadarChart>
                </ResponsiveContainer>
            </div>

            <div className="mt-4 grid grid-cols-3 gap-2 text-center text-xs">
                <div className="p-2 rounded bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-700/50">
                    <p className="text-zinc-500 dark:text-zinc-400 mb-1">Financial</p>
                    <p className="font-bold text-blue-500 dark:text-blue-400 text-sm">{data.breakdown.financial_risk}%</p>
                </div>
                <div className="p-2 rounded bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-700/50">
                    <p className="text-zinc-500 dark:text-zinc-400 mb-1">Operational</p>
                    <p className="font-bold text-purple-500 dark:text-purple-400 text-sm">{data.breakdown.operational_risk}%</p>
                </div>
                <div className="p-2 rounded bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-100 dark:border-zinc-700/50">
                    <p className="text-zinc-500 dark:text-zinc-400 mb-1">Client</p>
                    <p className="font-bold text-orange-500 dark:text-orange-400 text-sm">{data.breakdown.client_risk}%</p>
                </div>
            </div>
        </div>
    );
};

export default RiskRadar;
