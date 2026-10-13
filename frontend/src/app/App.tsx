import { ComparisonPage } from '../features/comparison/ComparisonPage';

export function App() {
  return <>
    <header className="border-b border-line">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-5 sm:px-6">
        <a href="/" className="flex items-center gap-3 text-accent" aria-label="Career Intelligence, inicio"><span className="text-2xl font-extrabold tracking-tight">CI</span><span className="text-sm font-semibold">Career Intelligence</span></a>
        <span className="text-xs text-muted">Sesión local · privada</span>
      </div>
    </header>
    <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 sm:py-10"><ComparisonPage /></main>
    <footer className="mx-auto max-w-6xl px-4 pb-8 text-center text-xs leading-5 text-muted">Diccionario y reglas revisables · Sin inferencias de años de experiencia, nivel de dominio o seniority.</footer>
  </>;
}
