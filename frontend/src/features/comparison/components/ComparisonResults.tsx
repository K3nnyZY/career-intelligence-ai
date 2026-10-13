import { useEffect, useRef } from 'react';
import type { Comparison, Evidence, Requirement } from '../api/contracts';

const labels: Record<Requirement, string> = { required: 'Obligatorias', desirable: 'Deseables', unspecified: 'Sin clasificación explícita' };
const groups: Requirement[] = ['required', 'desirable', 'unspecified'];

function EvidenceQuotes({ items }: { items: Evidence[] }) {
  return [...new Set(items.map((item) => item.quote))].map((quote) =>
    <blockquote key={quote} className="my-3 border-l-3 border-accent/25 pl-4 text-sm leading-6 whitespace-pre-wrap text-muted">{quote}</blockquote>);
}

export function ComparisonResults({ result }: { result: Comparison }) {
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { heading.current?.focus(); }, [result]);
  return <section id="results" aria-labelledby="results-heading" className="mt-6 rounded-2xl border border-line bg-white p-6 md:p-8">
    <p className="text-xs font-bold tracking-[0.16em] text-accent">03 / TU COMPARACIÓN</p>
    <h2 id="results-heading" ref={heading} tabIndex={-1} className="mt-2 mb-6 text-2xl font-semibold tracking-tight">Una lectura con respaldo</h2>
    <div id="summary" className="grid gap-4 sm:grid-cols-3">
      {groups.map((key) => { const group = result.groups[key]; const total = group.matched.length + group.missing_evidence.length;
        return <article key={key} className="rounded-lg border border-line p-4">
          <p className="text-xs text-muted">{labels[key]}</p>
          <strong className="mt-2 block text-2xl font-semibold">{total ? `${group.matched.length} / ${total}` : 'Sin menciones'}</strong>
          <p className="mt-1 text-xs text-muted">{group.coverage === null ? 'No se calcula cobertura' : `${Math.round(group.coverage * 100)}% de cobertura reconocida`}</p>
        </article>;
      })}
    </div>
    <div className="my-5 space-y-2 text-xs leading-5 text-muted">{result.warnings.map((warning) => <p key={warning}>{warning}</p>)}</div>
    <div id="matches">{result.skills.map((row) => <article key={row.skill} className="border-b border-line py-5">
      <div className="flex flex-wrap items-center gap-3">
        <h3 className="font-semibold">{row.skill}</h3>
        <span className="rounded bg-tint px-2 py-1 text-xs">{labels[row.requirement]}</span>
        <span className={`rounded px-2 py-1 text-xs ${row.status === 'matched' ? 'bg-tint' : 'bg-amber-50 text-amber-900'}`}>{row.status === 'matched' ? 'Coincide' : 'Sin evidencia en el CV'}</span>
      </div>
      <div className="mt-3 grid gap-3 md:grid-cols-2 md:gap-6">
        <div><h4 className="text-xs font-semibold">CV revisado</h4>
          {row.cv_evidence.length ? <EvidenceQuotes items={row.cv_evidence} /> : <p className="mt-3 text-xs leading-5 text-muted">No hay una mención seleccionada que respalde esta habilidad.</p>}
        </div>
        <div><h4 className="text-xs font-semibold">Vacante</h4><EvidenceQuotes items={row.vacancy_evidence} /></div>
      </div>
    </article>)}</div>
    <h3 className="mt-6 font-semibold">Experiencia que puedes destacar</h3>
    <div id="highlights" className="mt-3">
      {result.highlights.map((highlight) => <div key={`${highlight.start}-${highlight.end}`}>
        <p className="text-xs text-muted">Relevante para: {highlight.relevant_skills.join(', ')}</p>
        <blockquote className="my-3 border-l-3 border-accent/25 pl-4 text-sm leading-6 whitespace-pre-wrap text-muted">{highlight.quote}</blockquote>
      </div>)}
      {!result.highlights.length && <p className="text-xs leading-5 text-muted">No se detectaron fragmentos de experiencia relacionados con las coincidencias. Revisa manualmente los proyectos relevantes.</p>}
    </div>
    <details className="mt-6 text-sm"><summary className="font-semibold">Menciones excluidas por negación</summary>
      {result.excluded_mentions.length ? <EvidenceQuotes items={result.excluded_mentions} /> : <p className="mt-3 text-xs text-muted">No se detectaron menciones negadas.</p>}
    </details>
  </section>;
}
