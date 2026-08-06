import { AlertTriangle, CheckCircle2, RefreshCw } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import type { JDMatchResult } from '@/types/jd'

interface MatchResultPanelProps {
  match: JDMatchResult | null
  loading?: boolean
  recomputing?: boolean
  onRecompute?: () => void
}

function percent(value: number | null | undefined) {
  if (value === null || value === undefined) return '—'
  return `${Math.round(value * 100)}%`
}

export function MatchResultPanel({ match, loading, recomputing, onRecompute }: MatchResultPanelProps) {
  const { t } = useTranslation()
  if (loading) {
    return <Card><CardHeader><CardTitle>{t('jd.matchPanel')}</CardTitle></CardHeader><CardContent>{t('common.loading')}</CardContent></Card>
  }
  if (!match) {
    return <Card><CardHeader><CardTitle>{t('jd.matchPanel')}</CardTitle></CardHeader><CardContent className="text-sm text-muted-foreground">{t('jd.matchEmpty')}</CardContent></Card>
  }
  const evidenceById = new Map((match.evidence || []).map((item) => [item.id, item]))
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {t('jd.matchPanel')}
          <Badge variant="neutral">{match.mode}</Badge>
          <Badge>{match.status}</Badge>
          {match.stale && <Badge className="bg-yellow-400 text-black">stale</Badge>}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-4">
          <div><p className="text-xs uppercase text-muted-foreground">Score</p><p className="text-2xl font-black">{match.match_score ?? '—'}</p></div>
          <div><p className="text-xs uppercase text-muted-foreground">Recommendation</p><p className="font-heading">{match.recommendation}</p></div>
          <div><p className="text-xs uppercase text-muted-foreground">{t('jd.coverage')}</p><p className="font-heading">{percent(match.coverage)}</p></div>
          <div><p className="text-xs uppercase text-muted-foreground">{t('jd.confidence')}</p><p className="font-heading">{percent(match.confidence)}</p></div>
        </div>
        <div className="rounded-base border-2 border-black bg-secondary-background p-3 text-sm">
          <AlertTriangle className="mr-2 inline size-4" />{t('jd.modelDisclaimer')}
        </div>
        {match.stale && (
          <div className="space-y-2">
            <p className="font-heading">{t('jd.staleReasons')}</p>
            <div className="flex flex-wrap gap-2">{match.stale_reasons.map((reason) => <Badge key={reason} variant="neutral">{reason}</Badge>)}</div>
            {onRecompute && <Button onClick={onRecompute} disabled={recomputing}><RefreshCw className={recomputing ? 'size-4 animate-spin' : 'size-4'} />{t('jd.recompute')}</Button>}
          </div>
        )}
        <div className="space-y-2">
          <p className="font-heading">{t('jd.hardFilters')}</p>
          {match.hard_filters?.length ? match.hard_filters.map((item) => (
            <div key={item.requirement_id} className="rounded-base border-2 border-black p-3 text-sm">
              <div className="flex flex-wrap items-center gap-2"><Badge>{item.status}</Badge><span className="font-heading">{item.type}</span>{item.human_confirmation_required && <Badge className="bg-yellow-400 text-black">human review</Badge>}</div>
              <p className="mt-1 text-muted-foreground">{item.reason}</p>
            </div>
          )) : <p className="text-sm text-muted-foreground">—</p>}
        </div>
        <div className="space-y-2">
          <p className="font-heading">{t('jd.dimensions')}</p>
          {match.dimension_scores?.map((dimension) => (
            <div key={dimension.dimension} className="rounded-base border-2 border-black p-3 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <span className="font-heading">{dimension.dimension}</span>
                <span>{dimension.score ?? '—'} / 100 · {dimension.status}</span>
              </div>
              <p className="mt-1 text-muted-foreground">{dimension.reason}</p>
              <div className="mt-2 flex flex-wrap gap-1">
                {[...dimension.jd_evidence_ids, ...dimension.candidate_evidence_ids].map((id) => <Badge key={id} variant="neutral">{id}</Badge>)}
              </div>
            </div>
          ))}
        </div>
        <div className="space-y-2">
          <p className="font-heading">{t('jd.evidence')}</p>
          <div className="grid gap-2 md:grid-cols-2">
            {(match.evidence || []).slice(0, 12).map((item) => (
              <div key={item.id} className="rounded-base border border-black/30 p-2 text-xs">
                <div className="flex items-center gap-1 font-heading"><CheckCircle2 className="size-3" />{item.id} · {item.source}</div>
                <p className="mt-1 line-clamp-3 text-muted-foreground">{evidenceById.get(item.id)?.excerpt}</p>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
