import React, { useState, useEffect } from 'react';
import { motion, useAnimation } from 'framer-motion';
import { TrendingUp, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import StatusBadge from './StatusBadge';
import TrendIndicator from './TrendIndicator';

const KpiCard = React.memo(({ kpi, index = 0 }) => {
    const { name, value, target_min, target_max, status, last_updated, unit_type, previous_value, delta_percent } = kpi;
    const [displayValue, setDisplayValue] = useState(0);
    const controls = useAnimation();

    const formatKPI = (val, type) => {
        if (val === null || val === undefined) return 'N/A';
        switch (type) {
            case "percentage":
                return val.toFixed(2) + "%";
            case "currency":
                return "₹" + val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
            case "count":
                return Math.round(val);
            case "rating":
                return val.toFixed(2) + " / 5";
            case "ratio":
                return val.toFixed(2);
            default:
                return typeof val === 'number' ? val.toFixed(2) : val;
        }
    };

    // Count-up animation
    useEffect(() => {
        if (value && typeof value === 'number') {
            const duration = 1000; // 1 second
            const steps = 60;
            const increment = value / steps;
            let current = 0;

            const timer = setInterval(() => {
                current += increment;
                if (current >= value) {
                    setDisplayValue(value);
                    clearInterval(timer);
                } else {
                    setDisplayValue(current);
                }
            }, duration / steps);

            return () => clearInterval(timer);
        }
    }, [value]);

    const formattedValue = formatKPI(displayValue, unit_type);

    // Semantic color glow system
    const getCardStyles = () => {
        const baseStyles = "backdrop-blur-sm rounded-xl p-6 transition-all shadow-lg flex flex-col justify-between h-full";

        switch (status) {
            case 'critical':
                return `${baseStyles} bg-white/80 dark:bg-zinc-900/50 border border-red-200 dark:border-red-500/30 hover:border-red-400 dark:hover:border-red-500/50 hover:bg-red-50 dark:hover:bg-red-500/5`;
            case 'at_risk':
                return `${baseStyles} bg-white/80 dark:bg-zinc-900/50 border border-amber-200 dark:border-amber-500/30 hover:border-amber-400 dark:hover:border-amber-500/50 hover:bg-amber-50 dark:hover:bg-amber-500/5`;
            case 'on_track':
                return `${baseStyles} bg-white/80 dark:bg-zinc-900/50 border border-green-200 dark:border-green-500/30 hover:border-green-400 dark:hover:border-green-500/50 hover:bg-green-50 dark:hover:bg-green-500/5`;
            default:
                return `${baseStyles} bg-white/80 dark:bg-zinc-900/50 border border-zinc-200 dark:border-zinc-800 hover:border-zinc-300 dark:hover:border-zinc-700`;
        }
    };

    // Target Display
    let targetText = '';
    const formattedMin = target_min !== null ? formatKPI(target_min, unit_type) : null;
    const formattedMax = target_max !== null ? formatKPI(target_max, unit_type) : null;

    if (target_min !== null && target_max !== null) {
        targetText = `${formattedMin} - ${formattedMax}`;
    } else if (target_min !== null) {
        targetText = `>= ${formattedMin}`;
    } else if (target_max !== null) {
        targetText = `<= ${formattedMax}`;
    }

    // Time format
    const timeStr = last_updated ? new Date(last_updated).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--';

    return (
        <motion.div
            className={getCardStyles()}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 0.95, y: 0 }}
            transition={{
                duration: 0.3,
                delay: index * 0.05,
                ease: "easeOut"
            }}
            whileHover={{
                scale: 1.02,
                opacity: 1,
                transition: { duration: 0.2 }
            }}
        >
            {/* Header */}
            <div className="flex flex-col gap-2 mb-4">
                <h3 className="text-zinc-600 dark:text-zinc-300 font-medium text-sm uppercase tracking-wide" title={name}>
                    {name}
                </h3>
                <motion.div
                    className="self-start"
                    animate={status === 'critical' ? {
                        scale: [1, 1.1, 1],
                    } : {}}
                    transition={{
                        duration: 2,
                        repeat: status === 'critical' ? Infinity : 0,
                        ease: "easeInOut"
                    }}
                >
                    <StatusBadge status={status} />
                </motion.div>
            </div>

            {/* Main Value */}
            <div className="mb-2">
                <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold text-zinc-900 dark:text-white">{formattedValue}</span>
                </div>
                <TrendIndicator delta_percent={delta_percent} previous_value={previous_value} />
            </div>

            {/* Footer Info */}
            <div className="mt-auto pt-4 border-t border-zinc-200 dark:border-zinc-800/50 flex justify-between items-center text-xs">
                <div className="flex flex-col">
                    <span className="text-zinc-400 dark:text-zinc-500">Target</span>
                    <span className="text-zinc-600 dark:text-zinc-300 font-mono">{targetText || 'N/A'}</span>
                </div>

                <div className="flex flex-col items-end gap-1">
                    {kpi.time_scope && (
                        <span className="px-2 py-0.5 rounded-full bg-zinc-100 dark:bg-zinc-800 text-zinc-500 dark:text-zinc-400 text-[10px] uppercase tracking-wider font-semibold">
                            {kpi.time_scope.replace(/_/g, ' ')}
                        </span>
                    )}
                    <div className="flex items-center gap-1.5 text-zinc-400 dark:text-zinc-600" title={`Updated at ${last_updated}`}>
                        <Clock size={12} />
                        <span>{timeStr}</span>
                    </div>
                </div>
            </div>
        </motion.div>
    );
});

KpiCard.displayName = 'KpiCard';

export default KpiCard;
