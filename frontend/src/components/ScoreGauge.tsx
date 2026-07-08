interface ScoreGaugeProps {
  score: number // 0-10
  size?: number
}

function getScoreColor(score: number): string {
  if (score >= 7) return '#22c55e' // green
  if (score >= 5) return '#eab308' // yellow
  return '#ef4444' // red
}

export function ScoreGauge({ score, size = 180 }: ScoreGaugeProps) {
  const strokeWidth = 12
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const progress = Math.min(Math.max(score / 10, 0), 1)
  const dashOffset = circumference * (1 - progress)
  const color = getScoreColor(score)
  const center = size / 2

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="drop-shadow-[3px_3px_0px_#000]"
    >
      {/* Background circle */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="#e0e0e0"
        strokeWidth={strokeWidth}
        strokeLinecap="round"
      />
      {/* Border ring */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke="#000"
        strokeWidth={strokeWidth + 4}
        strokeLinecap="round"
        opacity={0.15}
      />
      {/* Progress circle */}
      <circle
        cx={center}
        cy={center}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={dashOffset}
        transform={`rotate(-90 ${center} ${center})`}
        className="transition-[stroke-dashoffset] duration-1000 ease-out"
      />
      {/* Score text */}
      <text
        x={center}
        y={center - 8}
        textAnchor="middle"
        dominantBaseline="central"
        className="font-black"
        fontSize={size * 0.28}
        fill="#000"
      >
        {score.toFixed(1)}
      </text>
      <text
        x={center}
        y={center + size * 0.15}
        textAnchor="middle"
        dominantBaseline="central"
        className="font-bold"
        fontSize={size * 0.09}
        fill="#666"
      >
        / 10
      </text>
    </svg>
  )
}
