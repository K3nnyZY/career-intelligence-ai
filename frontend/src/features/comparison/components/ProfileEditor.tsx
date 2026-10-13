import { Button } from '../../../shared/ui/Button';
import { Panel } from '../../../shared/ui/Panel';
import { TextField } from '../../../shared/ui/TextField';
import type { ComparisonController } from '../model/useComparison';

export function ProfileEditor({ controller }: { controller: ComparisonController }) {
  const { state, busy, changeCV, upload, review, toggleSkill, confirm } = controller;
  return <Panel id="cv-heading" step="01 / TU PERFIL" title="Carga y revisa tu CV">
    <label htmlFor="cv-file" className="mb-2 block text-sm font-semibold">PDF o DOCX · máximo 5 MiB</label>
    <input id="cv-file" type="file" accept=".pdf,.docx" disabled={busy} autoComplete="off"
      className="w-full rounded-lg border border-dashed border-accent/40 bg-tint/40 p-4 text-sm file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-white file:px-3 file:py-2 file:text-sm file:font-medium file:text-accent disabled:opacity-50"
      onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ''; if (file) void upload(file); }} />
    <p className="mt-2 text-xs leading-5 text-muted">También puedes pegar el texto. Para un PDF escaneado, usa OCR local primero.</p>
    <TextField id="cv-text" label="Texto del CV · editable" rows={12} maxLength={100000}
      placeholder="Pega tu CV o carga un archivo para extraer su texto." value={state.cvText} readOnly={busy}
      onChange={(event) => changeCV(event.target.value)}
      hint="Corrige errores de lectura y añade habilidades omitidas en el texto. Después actualiza la extracción." />
    <Button id="review" className="mt-4" disabled={busy || !state.cvText.trim()} onClick={() => void review()}>
      {state.operation === 'review' ? 'Actualizando…' : 'Actualizar extracción'}
    </Button>
    {state.profile && <div id="profile" className="mt-6 border-t border-line pt-5">
      <h3 className="text-base font-semibold">Habilidades detectadas</h3>
      <p className="mt-2 text-xs leading-5 text-muted">Desmarca menciones que no representen tus habilidades.</p>
      <div id="skills" className="mt-3 flex flex-wrap gap-2">
        {state.profile.skills.map((skill) => <label key={skill} className="flex cursor-pointer items-center gap-2 rounded-md bg-tint px-3 py-2 text-xs font-medium">
          <input type="checkbox" value={skill} checked={state.selectedSkills.includes(skill)} disabled={busy}
            onChange={() => toggleSkill(skill)} className="size-4 accent-accent" />{skill}
        </label>)}
        {!state.profile.skills.length && <p className="text-xs text-muted">No se reconocieron habilidades. Revisa el texto; el diccionario puede omitir tecnologías.</p>}
      </div>
      <details className="my-5 text-sm">
        <summary className="font-semibold">Fragmentos de experiencia detectados</summary>
        {state.profile.experience_signals.map((signal) => <blockquote key={`${signal.start}-${signal.end}`} className="my-3 border-l-3 border-accent/25 pl-4 text-sm leading-6 whitespace-pre-wrap text-muted">{signal.quote}</blockquote>)}
        {!state.profile.experience_signals.length && <p className="mt-3 text-xs leading-5 text-muted">No se detectaron fragmentos de experiencia con estas reglas. Puedes revisar tu experiencia directamente en el texto.</p>}
      </details>
      {state.profile.warnings.map((warning) => <p key={warning} className="my-2 text-xs leading-5 text-muted">{warning}</p>)}
      <label className="mt-4 flex cursor-pointer items-start gap-3 text-sm leading-6">
        <input id="confirmed" type="checkbox" className="mt-1 size-4 shrink-0 accent-accent" checked={state.confirmed} disabled={busy}
          onChange={(event) => confirm(event.target.checked)} />Revisé el texto y las habilidades seleccionadas.
      </label>
    </div>}
  </Panel>;
}
