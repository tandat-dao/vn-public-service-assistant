export function ScoreBadge({ score }: { score: number }) {
  return <span className="score-badge">{score.toFixed(2)}</span>
}
