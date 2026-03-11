import React from 'react';
import { useTheme } from '../context/ThemeContext';

const EntityLogo = ({ className = "" }) => {
    const { theme } = useTheme();

    // Dark mode text is #f0ede8, Light mode text is #111
    const textColor = theme === 'dark' ? '#f0ede8' : '#111';

    return (
        <div className={`flex flex-col items-start gap-2.5 ${className}`}>
            <style>
                {`
          @keyframes logoUp {
            from { opacity: 0; transform: translateY(12px); }
            to   { opacity: 1; transform: translateY(0); }
          }
          @keyframes logoBlink {
            0%, 49%  { opacity: 1; }
            50%, 100% { opacity: 0; }
          }
        `}
            </style>
            <div
                className="flex items-baseline"
                style={{ animation: 'logoUp 1.2s 0.15s cubic-bezier(0.16,1,0.3,1) both' }}
            >
                <span
                    className="font-light tracking-[-0.03em]"
                    style={{
                        fontFamily: "'Space Grotesk', sans-serif",
                        fontSize: 'clamp(3rem, 9vw, 6.5rem)',
                        color: textColor
                    }}
                >
                    entit
                </span>
                <span
                    className="italic leading-none tracking-[-0.04em] relative"
                    style={{
                        fontFamily: "'DM Serif Text', serif",
                        fontSize: 'clamp(3.6rem, 10.8vw, 7.8rem)',
                        color: textColor,
                        top: '0.08em'
                    }}
                >
                    y
                </span>
                <span
                    className="font-light tracking-[-0.03em] ml-0.5"
                    style={{
                        fontFamily: "'Space Grotesk', sans-serif",
                        fontSize: 'clamp(3rem, 9vw, 6.5rem)',
                        color: textColor,
                        animation: 'logoUp 1.2s 0.3s cubic-bezier(0.16,1,0.3,1) both, logoBlink 1s 1.8s step-start infinite'
                    }}
                >
                    _
                </span>
            </div>
        </div>
    );
};

export default EntityLogo;
