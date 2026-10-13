import { Button } from '../../shared/ui/Button';
import { ComparisonResults } from './components/ComparisonResults';
import { ProfileEditor } from './components/ProfileEditor';
import { VacancyEditor } from './components/VacancyEditor';
import { useComparison } from './model/useComparison';

export function ComparisonPage() {
  const controller = useComparison();
  return <>
    <div className="mb-8 max-w-3xl">
      <p className="text-xs font-bold tracking-[0.16em] text-accent">PREPARA TU CANDIDATURA CON EVIDENCIA</p>
      <h1 className="mt-3 text-4xl leading-[1.12] font-bold tracking-[-0.04em] sm:text-5xl lg:text-6xl">Tu experiencia.<br />Los requisitos. <span className="text-accent">La conexión.</span></h1>
      <p className="mt-5 max-w-2xl text-lg leading-7 text-muted">Compara tu CV con una vacante, revisa qué coincide y encuentra la experiencia que puedes destacar.</p>
    </div>
    <aside className="flex flex-col gap-4 rounded-xl bg-tint p-5 sm:flex-row sm:items-center sm:justify-between sm:gap-6 sm:p-6">
      <div><h2 className="font-semibold">Tú controlas tus datos</h2><p className="mt-1 max-w-3xl text-sm leading-6">El CV se procesa en este equipo. La aplicación no guarda archivos, perfiles ni resultados, y no los envía a servicios externos. Borrar sesión limpia el contenido de esta página.</p></div>
      <Button id="clear" variant="secondary" className="shrink-0" onClick={() => controller.clear()}>Borrar sesión</Button>
    </aside>
    <p id="status" role="status" aria-live="polite" className={`mt-4 min-h-6 text-sm ${controller.state.feedback.tone === 'error' ? 'text-red-800' : 'text-accent'}`}>{controller.state.feedback.text}</p>
    <div className="mt-4 grid gap-6 lg:grid-cols-2" aria-busy={controller.busy}>
      <ProfileEditor controller={controller} /><VacancyEditor controller={controller} />
    </div>
    {controller.state.result && <ComparisonResults result={controller.state.result} />}
  </>;
}
