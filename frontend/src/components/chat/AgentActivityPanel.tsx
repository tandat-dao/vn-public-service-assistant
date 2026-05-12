'use client'

/**
 * AgentActivityPanel — collapsible real-time agent timeline (TASK-SHOWCASE).
 *
 * Displays the pipeline steps that ran for a single assistant message as a
 * vertical timeline with status icons (spinner → checkmark). Parallel waves
 * are rendered side-by-side with a "parallel" label.
 *
 * Placement: directly above the assistant message bubble it corresponds to.
 * Tied to that specific message — not a global sidebar.
 *
 * Auto-expand behaviour:
 *   - Expands when `pipeline_start` event arrives (isStreaming=true).
 *   - Collapses 3 seconds after `pipeline_complete` (unless env var overrides).
 *   - In demo mode (NEXT_PUBLIC_AGENT_ACTIVITY_DEFAULT_OPEN=true): always expanded.
 */

import { useEffect, useRef, useState } from 'react'
import type { PipelineEvent } from '@/lib/types'

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEMO_MODE =
  process.env.NEXT_PUBLIC_AGENT_ACTIVITY_DEFAULT_OPEN === 'true'

const WORKER_LABELS: Record<string, string> = {
  rag_fn: 'RAG',
  ocr_fn: 'OCR',
  form_filler_fn: 'Form filler',
}

const DOMAIN_LABELS: Record<string, string> = {
  housing: 'Nhà ở',
  civil_registration: 'Hộ tịch',
  adoption: 'Nuôi con nuôi',
}

const SCOPE_LABELS: Record<string, string> = {
  'VN': 'Quốc gia',
  'VN-HCM': 'TP. HCM',
  'VN-HN': 'Hà Nội',
  'VN-DN': 'Đà Nẵng',
}

function scopeLabel(scope: string | null): string {
  if (!scope) return ''
  return SCOPE_LABELS[scope] ?? scope
}

function workerLabel(name: string): string {
  return WORKER_LABELS[name] ?? name
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Spinner() {
  return (
    <span className="inline-block w-3.5 h-3.5 border-2 border-[var(--terracotta)] border-t-transparent rounded-full animate-spin" />
  )
}

function CheckIcon() {
  return (
    <span className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-green-500 text-white text-[0.55rem] font-bold flex-shrink-0">
      ✓
    </span>
  )
}

function RouterRow({ events }: { events: PipelineEvent[] }) {
  const planEvent = events.find((e) => e.type === 'plan_decided') as Extract<PipelineEvent, { type: 'plan_decided' }> | undefined
  const started = events.some((e) => e.type === 'pipeline_start')
  const done = !!planEvent

  if (!started) return null

  return (
    <div className="flex items-start gap-2 py-1">
      <div className="w-3.5 mt-0.5 flex-shrink-0">{done ? <CheckIcon /> : <Spinner />}</div>
      <div className="text-[0.68rem] leading-snug text-[var(--text-secondary)]">
        <span className="font-semibold text-[var(--text-primary)]">Router</span>
        {planEvent && (
          <>
            {' '}
            <span className="text-[var(--text-muted)]">
              → [{planEvent.execution_plan.map(workerLabel).join(', ') || 'none'}]
            </span>
            {planEvent.domain && (
              <span className="ml-1 text-[var(--text-muted)]">
                · {DOMAIN_LABELS[planEvent.domain] ?? planEvent.domain}
              </span>
            )}
            {planEvent.location_scope && (
              <span className="ml-1 text-[var(--text-muted)]">
                · {scopeLabel(planEvent.location_scope)}
              </span>
            )}
          </>
        )}
      </div>
    </div>
  )
}

interface WaveGroup {
  workers: string[]
  waveIndex: number
  isParallel: boolean
  startedWorkers: Set<string>
  completedWorkers: Set<string>
  durationMs: number | null
  ragResult?: Extract<PipelineEvent, { type: 'rag_result' }>
  ocrResult?: Extract<PipelineEvent, { type: 'ocr_result' }>
  formResult?: Extract<PipelineEvent, { type: 'form_result' }>
}

function WaveRow({ wave }: { wave: WaveGroup }) {
  const allDone = wave.workers.every((w) => wave.completedWorkers.has(w))

  return (
    <div className="py-1">
      {wave.isParallel && (
        <div className="flex items-center gap-1 mb-0.5">
          <div className="h-px flex-1 bg-[var(--border-card)]" />
          <span className="text-[0.58rem] text-[var(--text-muted)] px-1">song song</span>
          <div className="h-px flex-1 bg-[var(--border-card)]" />
        </div>
      )}

      <div className={wave.isParallel ? 'pl-2 flex flex-col gap-0.5' : ''}>
        {wave.workers.map((worker) => {
          const started = wave.startedWorkers.has(worker)
          const done = wave.completedWorkers.has(worker)
          const icon = done ? <CheckIcon /> : started ? <Spinner /> : null

          // Per-worker detail line
          let detail: React.ReactNode = null
          if (worker === 'rag_fn' && wave.ragResult) {
            const r = wave.ragResult
            detail = (
              <span className="text-[var(--text-muted)]">
                {r.chunk_count} chunks · {scopeLabel(r.scope_used) || r.scope_used} · {r.confidence_tier} confidence
                {r.top_article ? ` · ${r.top_article}` : ''}
              </span>
            )
          } else if (worker === 'ocr_fn' && wave.ocrResult) {
            const o = wave.ocrResult
            detail = (
              <span className="text-[var(--text-muted)]">
                {o.document_type} · {o.field_count} trường · confidence {(o.confidence * 100).toFixed(0)}%
              </span>
            )
          } else if (worker === 'form_filler_fn' && wave.formResult) {
            const f = wave.formResult
            detail = (
              <span className="text-[var(--text-muted)]">
                {f.filled_count} trường đã điền
                {f.unfilled_required.length > 0
                  ? ` · thiếu: ${f.unfilled_required.slice(0, 3).join(', ')}${f.unfilled_required.length > 3 ? '…' : ''}`
                  : ''}
              </span>
            )
          }

          return (
            <div key={worker} className="flex items-start gap-2">
              <div className="w-3.5 mt-0.5 flex-shrink-0">{icon}</div>
              <div className="text-[0.68rem] leading-snug text-[var(--text-secondary)]">
                <span className="font-semibold text-[var(--text-primary)]">{workerLabel(worker)}</span>
                {done && wave.durationMs !== null && (
                  <span className="ml-1 text-[var(--text-muted)] text-[0.6rem]">
                    ({wave.durationMs}ms)
                  </span>
                )}
                {detail && <> {detail}</>}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function SynthesizerRow({ events }: { events: PipelineEvent[] }) {
  const completeEvent = events.find((e) => e.type === 'pipeline_complete') as Extract<PipelineEvent, { type: 'pipeline_complete' }> | undefined
  const started = events.some((e) => e.type === 'plan_decided')
  if (!started) return null

  return (
    <div className="flex items-start gap-2 py-1">
      <div className="w-3.5 mt-0.5 flex-shrink-0">{completeEvent ? <CheckIcon /> : <Spinner />}</div>
      <div className="text-[0.68rem] leading-snug text-[var(--text-secondary)]">
        <span className="font-semibold text-[var(--text-primary)]">Synthesizer</span>
        {completeEvent && (
          <span className="ml-1 text-[var(--text-muted)]">
            Mode: {completeEvent.synthesizer_mode}
          </span>
        )}
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Wave computation from event stream
// ---------------------------------------------------------------------------

function buildWaves(events: PipelineEvent[]): WaveGroup[] {
  const waves: WaveGroup[] = []

  for (const ev of events) {
    if (ev.type === 'parallel_wave_start') {
      waves.push({
        workers: ev.workers,
        waveIndex: ev.wave_index,
        isParallel: true,
        startedWorkers: new Set(),
        completedWorkers: new Set(),
        durationMs: null,
      })
    } else if (ev.type === 'worker_start') {
      // Find or create the wave this worker belongs to
      const wave = waves.find((w) => w.workers.includes(ev.worker) && !w.completedWorkers.has(ev.worker))
      if (wave) {
        wave.startedWorkers.add(ev.worker)
      } else {
        // Sequential worker (no prior parallel_wave_start for this worker)
        waves.push({
          workers: [ev.worker],
          waveIndex: waves.length,
          isParallel: false,
          startedWorkers: new Set([ev.worker]),
          completedWorkers: new Set(),
          durationMs: null,
        })
      }
    } else if (ev.type === 'worker_complete') {
      const wave = waves.find((w) => w.workers.includes(ev.worker) && !w.completedWorkers.has(ev.worker))
      if (wave) {
        wave.completedWorkers.add(ev.worker)
        wave.durationMs = ev.duration_ms
      }
    } else if (ev.type === 'rag_result') {
      const wave = waves.find((w) => w.workers.includes('rag_fn'))
      if (wave) wave.ragResult = ev as Extract<PipelineEvent, { type: 'rag_result' }>
    } else if (ev.type === 'ocr_result') {
      const wave = waves.find((w) => w.workers.includes('ocr_fn'))
      if (wave) wave.ocrResult = ev as Extract<PipelineEvent, { type: 'ocr_result' }>
    } else if (ev.type === 'form_result') {
      const wave = waves.find((w) => w.workers.includes('form_filler_fn'))
      if (wave) wave.formResult = ev as Extract<PipelineEvent, { type: 'form_result' }>
    }
  }

  return waves
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

interface AgentActivityPanelProps {
  messageId: string
  events: PipelineEvent[]
  isMessageStreaming: boolean
}

export function AgentActivityPanel({ messageId, events, isMessageStreaming }: AgentActivityPanelProps) {
  const [isOpen, setIsOpen] = useState(DEMO_MODE)
  const collapseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Auto-expand when pipeline starts, auto-collapse after complete (unless demo mode)
  useEffect(() => {
    const hasPipelineStart = events.some((e) => e.type === 'pipeline_start')
    const hasComplete = events.some((e) => e.type === 'pipeline_complete')

    if (hasPipelineStart && !isOpen && !DEMO_MODE) {
      setIsOpen(true)
    }

    if (hasComplete && !isMessageStreaming && !DEMO_MODE) {
      if (collapseTimerRef.current) clearTimeout(collapseTimerRef.current)
      collapseTimerRef.current = setTimeout(() => setIsOpen(false), 3000)
    }

    return () => {
      if (collapseTimerRef.current) clearTimeout(collapseTimerRef.current)
    }
  }, [events, isMessageStreaming]) // eslint-disable-line react-hooks/exhaustive-deps

  if (events.length === 0) return null

  const completeEvent = events.find((e) => e.type === 'pipeline_complete') as Extract<PipelineEvent, { type: 'pipeline_complete' }> | undefined
  const planEvent = events.find((e) => e.type === 'plan_decided') as Extract<PipelineEvent, { type: 'plan_decided' }> | undefined
  const waves = buildWaves(events)

  // Collapsed summary line
  const totalSteps = (planEvent?.execution_plan.length ?? 0) + 2 // router + workers + synth
  const totalMs = completeEvent?.total_ms

  return (
    <div className="mb-1.5 w-full max-w-[80%] text-[0.68rem]">
      {/* Toggle bar */}
      <button
        onClick={() => setIsOpen((v) => !v)}
        className="flex items-center gap-1.5 w-full text-left px-2 py-1
                   bg-[var(--navy-faint)] border border-[var(--border-card)]
                   rounded-[4px] hover:bg-[var(--navy-light)] transition-colors
                   text-[var(--text-muted)]"
      >
        <span className="text-[0.6rem]">{isOpen ? '▼' : '▶'}</span>
        <span className="flex-1 truncate">
          {isOpen
            ? `Agent Activity  (${waves.length} bước${totalMs ? `, ${(totalMs / 1000).toFixed(1)}s` : ''})`
            : completeEvent
              ? `Agent: ${totalSteps} bước · ${(totalMs! / 1000).toFixed(1)}s · ${planEvent?.execution_plan.map(workerLabel).join(' · ') || '—'}`
              : isMessageStreaming
                ? 'Agent đang xử lý…'
                : 'Agent Activity'
          }
        </span>
      </button>

      {/* Expanded timeline */}
      {isOpen && (
        <div className="mt-0.5 px-3 py-1.5 bg-white border border-[var(--border-card)] rounded-[4px]
                        divide-y divide-[var(--border-card)]">
          <RouterRow events={events} />
          {waves.map((wave, i) => (
            <WaveRow key={i} wave={wave} />
          ))}
          <SynthesizerRow events={events} />
        </div>
      )}
    </div>
  )
}
