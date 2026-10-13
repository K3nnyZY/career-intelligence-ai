import { defineConfig, devices } from '@playwright/test';

const python = process.env.CAREER_AI_PYTHON ?? 'python3';
const quotedPython = "'" + python.replaceAll("'", "'\\''") + "'";

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
    launchOptions: process.env.CAREER_AI_CHROME ? { executablePath: process.env.CAREER_AI_CHROME } : {},
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `${quotedPython} -m uvicorn career_ai.api:app --host 127.0.0.1 --port 8000 --no-access-log`,
    cwd: '..',
    url: 'http://127.0.0.1:8000/health',
    reuseExistingServer: !process.env.CI,
    timeout: 30000,
  },
});
