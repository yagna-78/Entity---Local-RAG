import React from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const TrendIndicator = ({ delta_percent, previous_value }) => {
    // Don't show if no historical data
    if (previous_value === null || previous_value === undefined || delta_percent === null || delta_percent === undefined) {
        return null;
    }

    const isPositive = delta_percent > 0;
    const isNeutral = delta_percent === 0;
    const absValue = Math.abs(delta_percent);

    return (
        <div className={`flex items-center gap-1 text-xs font-bold ${isNeutral ? 'text-zinc-500' :
            isPositive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            }`}>
            {isNeutral ? (
                <Minus size={12} />
            ) : isPositive ? (
                <TrendingUp size={12} />
            ) : (
                <TrendingDown size={12} />
            )}
            <span>
                {isPositive && '+'}{absValue.toFixed(1)}%
            </span>
        </div>
    );
};

export default TrendIndicator;
