interface SentimentGaugeProps {
  value: number; // -1 to 1
  size?: number;
  showLabel?: boolean;
}

export function SentimentGauge({ value, size = 120, showLabel = true }: SentimentGaugeProps) {
  // Clamp value between -1 and 1
  const clampedValue = Math.max(-1, Math.min(1, value));

  // Convert to 0-180 degrees (left to right arc)
  const angle = ((clampedValue + 1) / 2) * 180;

  // Calculate needle position
  const needleAngle = angle - 90; // Adjust for SVG coordinate system
  const needleLength = size * 0.35;
  const centerX = size / 2;
  const centerY = size * 0.55;

  const needleX = centerX + needleLength * Math.cos((needleAngle * Math.PI) / 180);
  const needleY = centerY + needleLength * Math.sin((needleAngle * Math.PI) / 180);

  // Color based on sentiment
  const getColor = (val: number) => {
    if (val < -0.3) return '#ef4444'; // red
    if (val < 0) return '#f59e0b'; // amber
    if (val < 0.3) return '#84cc16'; // lime
    return '#22c55e'; // green
  };

  const color = getColor(clampedValue);

  // Label based on sentiment
  const getLabel = (val: number) => {
    if (val < -0.5) return 'Negative';
    if (val < -0.2) return 'Slightly Negative';
    if (val < 0.2) return 'Neutral';
    if (val < 0.5) return 'Slightly Positive';
    return 'Positive';
  };

  const arcRadius = size * 0.38;
  const arcWidth = size * 0.08;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size * 0.65} viewBox={`0 0 ${size} ${size * 0.65}`}>
        {/* Background arc */}
        <path
          d={`M ${centerX - arcRadius} ${centerY} A ${arcRadius} ${arcRadius} 0 0 1 ${centerX + arcRadius} ${centerY}`}
          fill="none"
          stroke="rgba(255,255,255,0.1)"
          strokeWidth={arcWidth}
          strokeLinecap="round"
        />

        {/* Colored gradient arc sections */}
        <defs>
          <linearGradient id="sentimentGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#ef4444" />
            <stop offset="25%" stopColor="#f59e0b" />
            <stop offset="50%" stopColor="#84cc16" />
            <stop offset="75%" stopColor="#22c55e" />
            <stop offset="100%" stopColor="#22c55e" />
          </linearGradient>
        </defs>

        <path
          d={`M ${centerX - arcRadius} ${centerY} A ${arcRadius} ${arcRadius} 0 0 1 ${centerX + arcRadius} ${centerY}`}
          fill="none"
          stroke="url(#sentimentGradient)"
          strokeWidth={arcWidth}
          strokeLinecap="round"
          opacity={0.5}
        />

        {/* Needle */}
        <line
          x1={centerX}
          y1={centerY}
          x2={needleX}
          y2={needleY}
          stroke={color}
          strokeWidth={3}
          strokeLinecap="round"
          className="transition-all duration-500"
        />

        {/* Needle center dot */}
        <circle cx={centerX} cy={centerY} r={size * 0.04} fill={color} />

        {/* Min/Max labels */}
        <text
          x={centerX - arcRadius - 5}
          y={centerY + 15}
          fontSize={10}
          fill="rgba(255,255,255,0.5)"
          textAnchor="middle"
        >
          -1
        </text>
        <text
          x={centerX + arcRadius + 5}
          y={centerY + 15}
          fontSize={10}
          fill="rgba(255,255,255,0.5)"
          textAnchor="middle"
        >
          +1
        </text>

        {/* Value display */}
        <text
          x={centerX}
          y={centerY + size * 0.15}
          fontSize={14}
          fontWeight="bold"
          fill={color}
          textAnchor="middle"
        >
          {clampedValue.toFixed(2)}
        </text>
      </svg>

      {showLabel && (
        <span className="text-sm text-gray-400 mt-1">{getLabel(clampedValue)}</span>
      )}
    </div>
  );
}

export default SentimentGauge;
