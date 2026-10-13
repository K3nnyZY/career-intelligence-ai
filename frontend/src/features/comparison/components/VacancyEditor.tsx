import { Button } from '../../../shared/ui/Button';
import { Panel } from '../../../shared/ui/Panel';
import { TextField } from '../../../shared/ui/TextField';
import type { ComparisonController } from '../model/useComparison';

export function VacancyEditor({ controller }: { controller: ComparisonController }) {
  return <Panel id="job-heading" step="02 / LA OPORTUNIDAD" title="Pega la vacante">
    <TextField id="job-text" label="Descripción completa" rows={16} maxLength={50000} value={controller.state.vacancyText}
      placeholder="Incluye responsabilidades, requisitos obligatorios y habilidades deseables." readOnly={controller.busy}
      onChange={(event) => controller.changeVacancy(event.target.value)}
      hint="Usa una descripción que tengas permiso de analizar. Conserva los títulos de cada sección para ayudar a distinguir los requisitos." />
    <Button id="compare" className="mt-4" disabled={!controller.canCompare} onClick={() => void controller.compare()}>
      {controller.state.operation === 'compare' ? 'Comparando…' : 'Comparar con mi perfil'}
    </Button>
    <div className="mt-8 border-t border-line pt-5 text-sm leading-6 text-muted">
      <h3 className="font-semibold text-ink">Qué obtendrás</h3>
      <p className="mt-3">Coincidencias respaldadas por fragmentos, requisitos sin evidencia y experiencia relevante para tu candidatura.</p>
      <p className="mt-3">La cobertura mide menciones reconocidas. No estima tus posibilidades de contratación.</p>
    </div>
  </Panel>;
}
