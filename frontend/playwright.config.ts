import { defineConfig, devices } from '@playwright/test';

/**
 * Configuração Playwright para o frontend de geração musical.
 *
 * Todos os testes e2e usam route mocking para simular o backend —
 * não é necessário ter o servidor FastAPI em execução.
 *
 * Estrutura:
 *   tests/
 *     e2e/
 *       notation/    — fluxo assíncrono de partitura/tablatura
 *       generations/ — eliminação de gerações e cortes
 *     pages/
 *       AudioDetailPage.ts  — Page Object da página de detalhe de áudio
 */
export default defineConfig({
    testDir: './tests/e2e',
    fullyParallel: true,
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : undefined,
    reporter: [['html', { open: 'never' }]],

    use: {
        baseURL: 'http://localhost:5173',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
    },

    projects: [
        {
            name: 'chromium',
            use: { ...devices['Desktop Chrome'] },
        },
    ],

    webServer: {
        command: 'npm run dev',
        url: 'http://localhost:5173',
        reuseExistingServer: !process.env.CI,
        timeout: 30_000,
    },
});
