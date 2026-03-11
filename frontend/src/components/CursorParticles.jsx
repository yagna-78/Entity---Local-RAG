import React, { useEffect, useRef, useState } from 'react';

const CursorParticles = () => {
    const canvasRef = useRef(null);
    const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
    const mousePos = useRef({ x: 0, y: 0 });
    const particles = useRef([]);

    useEffect(() => {
        const updateDimensions = () => {
            if (canvasRef.current) {
                const parent = canvasRef.current.parentElement;
                setDimensions({
                    width: parent.clientWidth,
                    height: parent.clientHeight
                });
            }
        };

        updateDimensions();
        window.addEventListener('resize', updateDimensions);
        return () => window.removeEventListener('resize', updateDimensions);
    }, []);

    useEffect(() => {
        const canvas = canvasRef.current;
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        canvas.width = dimensions.width;
        canvas.height = dimensions.height;

        // Initialize particles - reduced to 8 for minimal effect
        const particleCount = 8;
        particles.current = Array.from({ length: particleCount }, () => ({
            x: Math.random() * dimensions.width,
            y: Math.random() * dimensions.height,
            vx: 0,
            vy: 0,
            size: Math.random() * 2.5 + 1.5,
            opacity: Math.random() * 0.4 + 0.4
        }));

        const handleMouseMove = (e) => {
            const rect = canvas.getBoundingClientRect();
            mousePos.current = {
                x: e.clientX - rect.left,
                y: e.clientY - rect.top
            };
        };

        canvas.addEventListener('mousemove', handleMouseMove);

        let animationId;
        const animate = () => {
            ctx.clearRect(0, 0, dimensions.width, dimensions.height);

            particles.current.forEach(particle => {
                // Calculate distance to cursor
                const dx = mousePos.current.x - particle.x;
                const dy = mousePos.current.y - particle.y;
                const distance = Math.sqrt(dx * dx + dy * dy);

                // Attract particles to cursor with stronger force
                if (distance < 250) {
                    const force = (250 - distance) / 250;
                    particle.vx += (dx / distance) * force * 0.15;
                    particle.vy += (dy / distance) * force * 0.15;
                }

                // Apply velocity with damping
                particle.x += particle.vx;
                particle.y += particle.vy;
                particle.vx *= 0.92;
                particle.vy *= 0.92;

                // Boundary wrapping
                if (particle.x < 0) particle.x = dimensions.width;
                if (particle.x > dimensions.width) particle.x = 0;
                if (particle.y < 0) particle.y = dimensions.height;
                if (particle.y > dimensions.height) particle.y = 0;

                // Draw particle with glow effect
                ctx.beginPath();
                ctx.arc(particle.x, particle.y, particle.size, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(255, 255, 255, ${particle.opacity})`;
                ctx.shadowBlur = 10;
                ctx.shadowColor = 'rgba(255, 255, 255, 0.5)';
                ctx.fill();
                ctx.shadowBlur = 0;
            });

            animationId = requestAnimationFrame(animate);
        };

        animate();

        return () => {
            cancelAnimationFrame(animationId);
            canvas.removeEventListener('mousemove', handleMouseMove);
        };
    }, [dimensions]);

    return (
        <canvas
            ref={canvasRef}
            className="pointer-events-none absolute inset-0 z-0"
            style={{ width: '100%', height: '100%' }}
        />
    );
};

export default CursorParticles;
