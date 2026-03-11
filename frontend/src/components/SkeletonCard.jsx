import React from 'react';

const SkeletonCard = () => {
    return (
        <div className="bg-zinc-900/50 backdrop-blur-sm border border-zinc-800 rounded-xl p-5 h-full animate-pulse">
            {/* Header skeleton */}
            <div className="flex justify-between items-start mb-4">
                <div className="h-4 bg-zinc-800 rounded w-2/3"></div>
                <div className="h-6 w-16 bg-zinc-800 rounded-full"></div>
            </div>

            {/* Value skeleton */}
            <div className="mb-4">
                <div className="h-10 bg-zinc-800 rounded w-1/2 mb-2"></div>
                <div className="h-3 bg-zinc-800 rounded w-1/4"></div>
            </div>

            {/* Footer skeleton */}
            <div className="mt-4 pt-4 border-t border-zinc-800/50 flex justify-between">
                <div className="h-3 bg-zinc-800 rounded w-1/4"></div>
                <div className="h-3 bg-zinc-800 rounded w-1/4"></div>
            </div>
        </div>
    );
};

export default SkeletonCard;
