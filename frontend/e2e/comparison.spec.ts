import { execFileSync } from 'node:child_process';
import { expect, test } from '@playwright/test';

test('DOCX, reviewed skills, evidence, responsive layout and session deletion', async ({ page, context }) => {
  const browserErrors: string[] = [];
  page.on('pageerror', (error) => browserErrors.push(error.message));
  const docx = execFileSync(process.env.CAREER_AI_PYTHON ?? 'python3', ['-c',
    'import sys; sys.path.insert(0, "../tests"); from document_fixtures import docx_bytes; sys.stdout.buffer.write(docx_bytes())']);
  await page.goto('/');
  await page.getByLabel('PDF o DOCX · máximo 5 MiB').setInputFiles({ name: 'synthetic.docx', mimeType: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', buffer: docx });
  await expect(page.getByRole('heading', { name: 'Habilidades detectadas' })).toBeVisible();
  await page.getByLabel('Texto del CV · editable').fill('Implementé procesos SQL y Python.\nMigré procesos a AWS.');
  await page.getByRole('button', { name: 'Actualizar extracción' }).click();
  await expect(page.getByRole('checkbox', { name: 'python', exact: true })).toBeVisible();
  await page.getByRole('checkbox', { name: 'python', exact: true }).uncheck();
  await page.getByRole('checkbox', { name: 'Revisé el texto y las habilidades seleccionadas.' }).check();
  await page.getByLabel('Descripción completa').fill('Requisitos obligatorios:\nSQL y Python\nDeseables:\nDocker');
  await page.getByRole('button', { name: 'Comparar con mi perfil' }).click();
  await expect(page.getByRole('heading', { name: 'Una lectura con respaldo' })).toBeVisible();
  await expect(page.locator('#summary')).toContainText('1 / 2');
  await expect(page.locator('#matches')).toContainText('Sin evidencia en el CV');
  await expect(page.locator('#highlights blockquote')).toHaveCount(1);
  expect(await page.evaluate(() => localStorage.length + sessionStorage.length)).toBe(0);
  expect(await context.cookies()).toHaveLength(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole('button', { name: 'Borrar sesión' }).click();
  await expect(page.getByLabel('Texto del CV · editable')).toHaveValue('');
  await expect(page.getByLabel('Descripción completa')).toHaveValue('');
  await expect(page.locator('#results')).toHaveCount(0);
  expect(browserErrors).toEqual([]);
});

test('a late response cannot restore a deleted CV', async ({ page }) => {
  await page.goto('/');
  let release = () => {};
  let complete = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  const fulfilled = new Promise<void>((resolve) => { complete = resolve; });
  await page.route('**/profile/review', async (route) => {
    await gate;
    await route.fulfill({ json: { text: 'Python', skills: ['python'], evidence: [], experience_signals: [], extractor_version: 'test', taxonomy_version: 'test', warnings: [] } });
    complete();
  });
  await page.getByLabel('Texto del CV · editable').fill('Python');
  const requestSeen = page.waitForRequest('**/profile/review');
  await page.getByRole('button', { name: 'Actualizar extracción' }).click();
  await requestSeen;
  await page.getByRole('button', { name: 'Borrar sesión' }).click();
  release();
  await fulfilled;
  await expect(page.getByRole('status')).toContainText('Sesión borrada');
  await expect(page.getByLabel('Texto del CV · editable')).toHaveValue('');
  await expect(page.getByRole('checkbox', { name: 'python', exact: true })).toHaveCount(0);
});
