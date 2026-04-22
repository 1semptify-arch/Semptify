/**
 * Semptify Confetti Celebration System
 * =====================================
 * 
 * Celebratory confetti effects for milestone achievements.
 * Designed to reinforce positive emotions and build momentum.
 * 
 * Usage:
 *   SemptifyConfetti.celebrate();           // Default celebration
 *   SemptifyConfetti.burst({ x: 0.5, y: 0.5 });  // Burst from center
 *   SemptifyConfetti.rain();                // Gentle rain effect
 *   SemptifyConfetti.fireworks();           // Multiple bursts
 */

const SemptifyConfetti = {
    // Configuration
    config: {
        particleCount: 100,
        spread: 70,
        startVelocity: 45,
        decay: 0.9,
        gravity: 1.2,
        ticks: 200,
        colors: [
            '#10b981',  // Success green
            '#3b82f6',  // Info blue
            '#8b5cf6',  // Milestone purple
            '#f59e0b',  // Warning yellow
            '#ec4899',  // Pink
            '#06b6d4',  // Cyan
        ],
        shapes: ['square', 'circle'],
        scalar: 1,
    },

    // Canvas element
    canvas: null,
    ctx: null,
    particles: [],
    animationId: null,

    /**
     * Initialize the confetti system
     */
    init() {
        if (this.canvas) return this;

        // Create canvas
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'semptify-confetti-canvas';
        this.canvas.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 99999;
        `;
        document.body.appendChild(this.canvas);

        this.ctx = this.canvas.getContext('2d');
        this.resizeCanvas();

        // Handle window resize
        window.addEventListener('resize', () => this.resizeCanvas());

        console.log('🎉 SemptifyConfetti initialized');
        return this;
    },

    /**
     * Resize canvas to window size
     */
    resizeCanvas() {
        if (!this.canvas) return;
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    },

    /**
     * Create a confetti particle
     */
    createParticle(x, y, options = {}) {
        const angle = options.angle || (Math.random() * Math.PI * 2);
        const velocity = options.velocity || (Math.random() * this.config.startVelocity + 20);
        const color = options.color || this.config.colors[Math.floor(Math.random() * this.config.colors.length)];
        const shape = options.shape || this.config.shapes[Math.floor(Math.random() * this.config.shapes.length)];

        return {
            x,
            y,
            vx: Math.cos(angle) * velocity,
            vy: Math.sin(angle) * velocity - (options.upward ? velocity * 0.5 : 0),
            color,
            shape,
            size: Math.random() * 8 + 4,
            rotation: Math.random() * 360,
            rotationSpeed: (Math.random() - 0.5) * 10,
            opacity: 1,
            gravity: this.config.gravity,
            decay: this.config.decay,
            ticks: this.config.ticks,
            ticksRemaining: this.config.ticks,
        };
    },

    /**
     * Draw a single particle
     */
    drawParticle(p) {
        this.ctx.save();
        this.ctx.translate(p.x, p.y);
        this.ctx.rotate((p.rotation * Math.PI) / 180);
        this.ctx.globalAlpha = p.opacity;
        this.ctx.fillStyle = p.color;

        if (p.shape === 'circle') {
            this.ctx.beginPath();
            this.ctx.arc(0, 0, p.size / 2, 0, Math.PI * 2);
            this.ctx.fill();
        } else if (p.shape === 'square') {
            this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
        } else if (p.shape === 'star') {
            this.drawStar(p.size / 2);
        }

        this.ctx.restore();
    },

    /**
     * Draw a star shape
     */
    drawStar(radius) {
        const spikes = 5;
        const innerRadius = radius * 0.5;
        
        this.ctx.beginPath();
        for (let i = 0; i < spikes * 2; i++) {
            const r = i % 2 === 0 ? radius : innerRadius;
            const angle = (i * Math.PI) / spikes - Math.PI / 2;
            const x = Math.cos(angle) * r;
            const y = Math.sin(angle) * r;
            if (i === 0) {
                this.ctx.moveTo(x, y);
            } else {
                this.ctx.lineTo(x, y);
            }
        }
        this.ctx.closePath();
        this.ctx.fill();
    },

    /**
     * Update particle physics
     */
    updateParticle(p) {
        p.vx *= p.decay;
        p.vy *= p.decay;
        p.vy += p.gravity;
        p.x += p.vx;
        p.y += p.vy;
        p.rotation += p.rotationSpeed;
        p.ticksRemaining--;
        p.opacity = p.ticksRemaining / p.ticks;

        return p.ticksRemaining > 0 && p.y < this.canvas.height + 100;
    },

    /**
     * Animation loop
     */
    animate() {
        if (!this.ctx) return;

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Update and draw particles
        this.particles = this.particles.filter(p => {
            const alive = this.updateParticle(p);
            if (alive) {
                this.drawParticle(p);
            }
            return alive;
        });

        // Continue animation if particles exist
        if (this.particles.length > 0) {
            this.animationId = requestAnimationFrame(() => this.animate());
        } else {
            this.animationId = null;
        }
    },

    /**
     * Start animation if not already running
     */
    startAnimation() {
        if (!this.animationId) {
            this.animate();
        }
    },

    /**
     * Default celebration effect
     */
    celebrate(options = {}) {
        this.init();

        const count = options.particleCount || this.config.particleCount;
        const x = (options.x !== undefined ? options.x : 0.5) * this.canvas.width;
        const y = (options.y !== undefined ? options.y : 0.3) * this.canvas.height;

        // Create burst particles
        for (let i = 0; i < count; i++) {
            const angle = (i / count) * Math.PI * 2;
            this.particles.push(this.createParticle(x, y, {
                angle,
                velocity: Math.random() * 30 + 30,
                upward: true,
            }));
        }

        this.startAnimation();
        return this;
    },

    /**
     * Burst effect from a specific point
     */
    burst(options = {}) {
        this.init();

        const count = options.particleCount || 50;
        const x = (options.x !== undefined ? options.x : 0.5) * this.canvas.width;
        const y = (options.y !== undefined ? options.y : 0.5) * this.canvas.height;

        for (let i = 0; i < count; i++) {
            this.particles.push(this.createParticle(x, y, {
                velocity: Math.random() * 40 + 20,
            }));
        }

        this.startAnimation();
        return this;
    },

    /**
     * Gentle rain effect from top
     */
    rain(options = {}) {
        this.init();

        const count = options.particleCount || 150;
        const duration = options.duration || 3000;
        const interval = duration / count;

        let spawned = 0;
        const spawnInterval = setInterval(() => {
            if (spawned >= count) {
                clearInterval(spawnInterval);
                return;
            }

            const x = Math.random() * this.canvas.width;
            const y = -20;
            
            this.particles.push(this.createParticle(x, y, {
                angle: Math.PI / 2 + (Math.random() - 0.5) * 0.5,
                velocity: Math.random() * 10 + 5,
            }));

            spawned++;
            this.startAnimation();
        }, interval);

        return this;
    },

    /**
     * Fireworks effect with multiple bursts
     */
    fireworks(options = {}) {
        this.init();

        const bursts = options.bursts || 5;
        const duration = options.duration || 2000;
        const interval = duration / bursts;

        for (let i = 0; i < bursts; i++) {
            setTimeout(() => {
                const x = 0.2 + Math.random() * 0.6;
                const y = 0.2 + Math.random() * 0.4;
                
                this.burst({
                    x,
                    y,
                    particleCount: 40 + Math.floor(Math.random() * 30),
                });
            }, i * interval);
        }

        return this;
    },

    /**
     * Side cannons effect (for big wins)
     */
    cannons(options = {}) {
        this.init();

        const count = options.particleCount || 100;

        // Left cannon
        for (let i = 0; i < count / 2; i++) {
            setTimeout(() => {
                this.particles.push(this.createParticle(0, this.canvas.height, {
                    angle: -Math.PI / 4 + (Math.random() - 0.5) * 0.5,
                    velocity: Math.random() * 50 + 40,
                }));
                this.startAnimation();
            }, Math.random() * 500);
        }

        // Right cannon
        for (let i = 0; i < count / 2; i++) {
            setTimeout(() => {
                this.particles.push(this.createParticle(this.canvas.width, this.canvas.height, {
                    angle: -Math.PI * 3 / 4 + (Math.random() - 0.5) * 0.5,
                    velocity: Math.random() * 50 + 40,
                }));
                this.startAnimation();
            }, Math.random() * 500);
        }

        return this;
    },

    /**
     * School pride effect (continuous celebration)
     */
    schoolPride(options = {}) {
        this.init();

        const duration = options.duration || 5000;
        const end = Date.now() + duration;

        const frame = () => {
            if (Date.now() > end) return;

            // Random confetti from top
            this.particles.push(this.createParticle(
                Math.random() * this.canvas.width,
                -10,
                {
                    angle: Math.PI / 2,
                    velocity: Math.random() * 3 + 2,
                }
            ));

            this.startAnimation();
            requestAnimationFrame(frame);
        };

        frame();
        return this;
    },

    /**
     * Milestone-specific celebration
     */
    milestone(milestoneName) {
        // Different effects for different milestones
        const effects = {
            'notice_uploaded': () => this.celebrate({ particleCount: 80 }),
            'evidence_gathered': () => this.fireworks({ bursts: 3 }),
            'answer_prepared': () => this.cannons(),
            'court_ready': () => this.schoolPride({ duration: 3000 }),
            'victory': () => {
                this.schoolPride({ duration: 5000 });
                setTimeout(() => this.fireworks({ bursts: 7 }), 1000);
            },
            'default': () => this.celebrate(),
        };

        const effect = effects[milestoneName] || effects.default;
        effect();

        return this;
    },

    /**
     * Stop all effects and clear particles
     */
    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
        this.particles = [];
        if (this.ctx) {
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
        return this;
    },

    /**
     * Check if animation is running
     */
    isRunning() {
        return this.animationId !== null;
    }
};

// Make globally available
window.SemptifyConfetti = SemptifyConfetti;

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SemptifyConfetti;
}
