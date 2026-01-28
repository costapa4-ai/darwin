import { useEffect, useRef, useState } from 'react';

export default function DreamVisualizer({ dreamStatus, currentDream }) {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const [time, setTime] = useState(0);

  // Color schemes for different dream types
  const dreamColorSchemes = {
    'algorithm_exploration': {
      primary: [138, 43, 226],    // Purple
      secondary: [75, 0, 130],    // Indigo
      accent: [147, 112, 219]     // Medium Purple
    },
    'pattern_discovery': {
      primary: [0, 191, 255],     // Deep Sky Blue
      secondary: [30, 144, 255],  // Dodger Blue
      accent: [135, 206, 250]     // Light Sky Blue
    },
    'optimization_experiment': {
      primary: [255, 215, 0],     // Gold
      secondary: [255, 140, 0],   // Dark Orange
      accent: [255, 165, 0]       // Orange
    },
    'hypothesis_testing': {
      primary: [0, 255, 127],     // Spring Green
      secondary: [46, 139, 87],   // Sea Green
      accent: [60, 179, 113]      // Medium Sea Green
    },
    'creative_coding': {
      primary: [255, 20, 147],    // Deep Pink
      secondary: [199, 21, 133],  // Medium Violet Red
      accent: [218, 112, 214]     // Orchid
    },
    'library_learning': {
      primary: [64, 224, 208],    // Turquoise
      secondary: [72, 209, 204],  // Medium Turquoise
      accent: [175, 238, 238]     // Pale Turquoise
    },
    'self_analysis': {
      primary: [255, 255, 0],     // Yellow
      secondary: [255, 215, 0],   // Gold
      accent: [255, 140, 0]       // Dark Orange
    },
    'idle': {
      primary: [128, 128, 128],   // Gray
      secondary: [105, 105, 105], // Dim Gray
      accent: [169, 169, 169]     // Dark Gray
    }
  };

  // Mandelbrot set calculation
  const mandelbrot = (cx, cy, maxIter = 100) => {
    let x = 0;
    let y = 0;
    let iter = 0;

    while (x * x + y * y <= 4 && iter < maxIter) {
      const xtemp = x * x - y * y + cx;
      y = 2 * x * y + cy;
      x = xtemp;
      iter++;
    }

    return iter;
  };

  // Kaleidoscope effect - mirror coordinates
  const applyKaleidoscope = (x, y, centerX, centerY, segments = 6) => {
    const dx = x - centerX;
    const dy = y - centerY;
    const angle = Math.atan2(dy, dx);
    const radius = Math.sqrt(dx * dx + dy * dy);

    // Mirror angle based on number of segments
    const segmentAngle = (Math.PI * 2) / segments;
    const mirroredAngle = (angle % segmentAngle + segmentAngle) % segmentAngle;

    // If in second half of segment, mirror again
    if (mirroredAngle > segmentAngle / 2) {
      const finalAngle = segmentAngle - mirroredAngle;
      return {
        x: centerX + radius * Math.cos(finalAngle),
        y: centerY + radius * Math.sin(finalAngle)
      };
    }

    return {
      x: centerX + radius * Math.cos(mirroredAngle),
      y: centerY + radius * Math.sin(mirroredAngle)
    };
  };

  // Get color based on iteration and dream type
  const getColor = (iter, maxIter, colors, time) => {
    if (iter === maxIter) {
      return [0, 0, 0, 255]; // Black for points in the set
    }

    // Smooth coloring with time-based animation
    const smoothIter = iter + 1 - Math.log(Math.log(iter + 1)) / Math.log(2);
    const colorIndex = (smoothIter / maxIter + time * 0.05) % 1;

    // Interpolate between colors
    const t = colorIndex * 3; // 3 colors to cycle through
    let r, g, b;

    if (t < 1) {
      // Interpolate between primary and secondary
      r = colors.primary[0] + (colors.secondary[0] - colors.primary[0]) * t;
      g = colors.primary[1] + (colors.secondary[1] - colors.primary[1]) * t;
      b = colors.primary[2] + (colors.secondary[2] - colors.primary[2]) * t;
    } else if (t < 2) {
      // Interpolate between secondary and accent
      const t2 = t - 1;
      r = colors.secondary[0] + (colors.accent[0] - colors.secondary[0]) * t2;
      g = colors.secondary[1] + (colors.accent[1] - colors.secondary[1]) * t2;
      b = colors.secondary[2] + (colors.accent[2] - colors.secondary[2]) * t2;
    } else {
      // Interpolate between accent and primary
      const t3 = t - 2;
      r = colors.accent[0] + (colors.primary[0] - colors.accent[0]) * t3;
      g = colors.accent[1] + (colors.primary[1] - colors.accent[1]) * t3;
      b = colors.accent[2] + (colors.primary[2] - colors.accent[2]) * t3;
    }

    // Add brightness variation based on iteration
    const brightness = 0.5 + (iter / maxIter) * 0.5;

    return [
      Math.floor(r * brightness),
      Math.floor(g * brightness),
      Math.floor(b * brightness),
      255
    ];
  };

  // Draw the visualization
  const draw = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const width = canvas.width;
    const height = canvas.height;

    const imageData = ctx.createImageData(width, height);
    const data = imageData.data;

    // Get color scheme based on dream type
    const dreamType = currentDream?.type || 'idle';
    const colors = dreamColorSchemes[dreamType] || dreamColorSchemes['idle'];

    // Zoom and pan based on time and dream progress
    const progress = currentDream?.progress || 0;
    const zoom = 1.5 + Math.sin(time * 0.1) * 0.5 + (progress / 100) * 0.5;
    const panX = Math.cos(time * 0.05) * 0.3;
    const panY = Math.sin(time * 0.07) * 0.3;

    const centerX = width / 2;
    const centerY = height / 2;

    // Number of kaleidoscope segments (varies by dream type)
    const segments = dreamType === 'pattern_discovery' ? 8 :
                     dreamType === 'creative_coding' ? 12 :
                     dreamType === 'algorithm_exploration' ? 6 : 6;

    // Render each pixel
    for (let py = 0; py < height; py++) {
      for (let px = 0; px < width; px++) {
        // Apply kaleidoscope effect
        const mirrored = applyKaleidoscope(px, py, centerX, centerY, segments);

        // Map to Mandelbrot coordinates
        const x0 = ((mirrored.x - centerX) / (width * zoom / 4)) + panX;
        const y0 = ((mirrored.y - centerY) / (height * zoom / 4)) + panY;

        // Calculate Mandelbrot
        const maxIter = 100;
        const iter = mandelbrot(x0, y0, maxIter);

        // Get color
        const color = getColor(iter, maxIter, colors, time);

        // Set pixel
        const index = (py * width + px) * 4;
        data[index] = color[0];
        data[index + 1] = color[1];
        data[index + 2] = color[2];
        data[index + 3] = color[3];
      }
    }

    ctx.putImageData(imageData, 0, 0);

    // Add glow effect for active dreams
    if (currentDream) {
      ctx.shadowBlur = 20;
      ctx.shadowColor = `rgb(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]})`;
      ctx.strokeStyle = `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, 0.5)`;
      ctx.lineWidth = 3;
      ctx.strokeRect(0, 0, width, height);
      ctx.shadowBlur = 0;
    }

    // Add pulsing center for active dreams
    if (currentDream) {
      const pulseRadius = 30 + Math.sin(time * 0.3) * 10;
      const gradient = ctx.createRadialGradient(
        centerX, centerY, 0,
        centerX, centerY, pulseRadius
      );
      gradient.addColorStop(0, `rgba(${colors.primary[0]}, ${colors.primary[1]}, ${colors.primary[2]}, 0.8)`);
      gradient.addColorStop(0.5, `rgba(${colors.accent[0]}, ${colors.accent[1]}, ${colors.accent[2]}, 0.4)`);
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.fillStyle = gradient;
      ctx.fillRect(centerX - pulseRadius, centerY - pulseRadius, pulseRadius * 2, pulseRadius * 2);
    }
  };

  // Animation loop
  useEffect(() => {
    const animate = () => {
      setTime(t => t + 1);
      draw();
      animationRef.current = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [currentDream, time]);

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        width={400}
        height={400}
        className="rounded-lg border border-purple-500/30 shadow-lg"
        style={{
          background: 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)'
        }}
      />

      {/* Dream Type Label */}
      <div className="absolute top-2 left-2 bg-black/70 backdrop-blur-sm px-3 py-1 rounded-lg border border-purple-500/50">
        <div className="text-xs text-purple-300 font-semibold">
          {currentDream ? (
            <>
              {currentDream.type.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
            </>
          ) : (
            'Idle'
          )}
        </div>
      </div>

      {/* Animation Info */}
      <div className="absolute bottom-2 right-2 bg-black/70 backdrop-blur-sm px-3 py-1 rounded-lg border border-purple-500/50">
        <div className="text-xs text-slate-300 font-mono">
          {currentDream ? (
            <span className="text-green-400">● Dreaming</span>
          ) : (
            <span className="text-slate-500">○ Idle</span>
          )}
        </div>
      </div>

      {/* Progress Indicator */}
      {currentDream && (
        <div className="absolute bottom-2 left-2 bg-black/70 backdrop-blur-sm px-3 py-1 rounded-lg border border-purple-500/50">
          <div className="text-xs text-purple-300 font-mono">
            {currentDream.progress}%
          </div>
        </div>
      )}

      {/* Info Text */}
      <div className="mt-3 text-center">
        <p className="text-xs text-slate-400 italic">
          {currentDream ? (
            'Visual representation of active dream exploration'
          ) : (
            'Awaiting dream state...'
          )}
        </p>
      </div>
    </div>
  );
}
