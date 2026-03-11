import React from 'react';

const StatusBadge = ({ status }) => {
    // Normalize status string
    const s = (status || '').toLowerCase();

    let colors = '';
    let label = '';

    switch (s) {
        case 'on_track':
            colors = 'bg-green-100 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-500 dark:border-green-500/20';
            label = 'On Track';
            break;
        case 'at_risk':
            colors = 'bg-yellow-100 text-yellow-700 border-yellow-200 dark:bg-yellow-500/10 dark:text-yellow-500 dark:border-yellow-500/20';
            label = 'At Risk';
            break;
        case 'critical':
            colors = 'bg-red-100 text-red-700 border-red-200 dark:bg-red-500/10 dark:text-red-500 dark:border-red-500/20';
            label = 'Critical';
            break;
        default:
            colors = 'bg-zinc-100 text-zinc-700 border-zinc-200 dark:bg-zinc-500/10 dark:text-zinc-500 dark:border-zinc-500/20';
            label = 'Unknown';
    }

    return (
        <span className={`px-2.5 py-0.5 rounded-full text-xs font-medium border ${colors}`}>
            {label}
        </span>
    );
};

export default StatusBadge;
