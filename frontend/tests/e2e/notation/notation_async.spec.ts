import { test, expect } from '@playwright/test';
import { AudioDetailPage } from '../../pages/AudioDetailPage';

// ---------------------------------------------------------------------------
// Dados de teste (UUIDs estáticos para route mocking determinístico)
// ---------------------------------------------------------------------------
const PROJECT_ID  = 'aaaaaaaa-0000-0000-0000-000000000001';
const AUDIO_ID    = 'bbbbbbbb-0000-0000-0000-000000000002';
const GEN_ID      = 'cccccccc-0000-0000-0000-000000000003';
const CUT_ID      = 'dddddddd-0000-0000-0000-000000000004';

const PARTITURA_URL  = 'https://r2.example.com/partitura/cut-001.pdf?token=aaa';
const TABLATURA_URL  = 'https://r2.example.com/tablature/cut-001.pdf?token=bbb';

// ---------------------------------------------------------------------------
// Helpers de mocking reutilizáveis
// ---------------------------------------------------------------------------

/** Simula autenticação OAuth — devolve utilizador válido. */
async function mockAuth(page: import('@playwright/test').Page) {
    // Rota real usada por checkAuth()/ProtectedRoute é /users/me (plural) —
    // ver src/services/request.ts. Sem isto o checkAuth() nunca chega a
    // fazer fetch (ver nota sobre a chave de localStorage abaixo) e mesmo
    // que chegasse, "/api/user/me" nunca dava match.
    await page.route('**/api/users/me', route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ id: 'user-001', username: 'testuser' }),
        })
    );
    // Injeta token JWT falso em localStorage antes da navegação. A chave
    // real é 'music_ai.access_token' (ver src/utils/auth.ts STORAGE_KEY);
    // com a chave errada, getAccessToken() devolve null, checkAuth() devolve
    // false sem sequer chamar a rede, e o ProtectedRoute redirecciona para
    // /login antes de qualquer asserção correr.
    await page.addInitScript(() => {
        localStorage.setItem('music_ai.access_token', 'fake.jwt.token');
    });
}

/** Mocks base da página audioDetail (audio + árvore + corte). */
async function mockAudioDetailBase(
    page: import('@playwright/test').Page,
    cutOverrides: Record<string, unknown> = {},
) {
    // Audio metadata
    await page.route(`**/api/audio/analysis/${AUDIO_ID}`, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                id: AUDIO_ID,
                storage_key: 'audio/test.wav',
                duration: 30.0,
                sample_rate: 44100,
                bpm: 120,
                key: 'C major',
                time_signature: '4/4',
            }),
        })
    );

    // Audio presigned URL
    await page.route(`**/api/audio/${AUDIO_ID}`, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ url: 'https://r2.example.com/audio/test.wav' }),
        })
    );

    // Geração root (completed, sem notação por defeito)
    await page.route(`**/api/generation/by-audio/${AUDIO_ID}`, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                generations: [{
                    id: GEN_ID,
                    status: 'completed',
                    project_id: PROJECT_ID,
                    audio_file_id: AUDIO_ID,
                    prompt: 'Guitarra clássica',
                    instrument: 'guitarra',
                    audio_storage_key: `generations/${GEN_ID}.mp3`,
                    partitura_status: null,
                    tablatura_status: null,
                    partitura_storage_key: null,
                    tablatura_storage_key: null,
                    created_at: new Date().toISOString(),
                }],
            }),
        })
    );

    // Cortes da geração
    await page.route(`**/api/generation/${GEN_ID}/cuts`, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                generations: [{
                    id: CUT_ID,
                    status: 'completed',
                    project_id: PROJECT_ID,
                    audio_file_id: AUDIO_ID,
                    parent_generation_id: GEN_ID,
                    prompt: `Corte de ${GEN_ID} (0.00s-15.00s)`,
                    instrument: 'guitarra',
                    audio_storage_key: `generations/cut_${CUT_ID}.wav`,
                    partitura_status:  cutOverrides.partitura_status  ?? null,
                    tablatura_status:  cutOverrides.tablatura_status  ?? null,
                    partitura_storage_key: cutOverrides.partitura_storage_key ?? null,
                    tablatura_storage_key: cutOverrides.tablatura_storage_key ?? null,
                    created_at: new Date().toISOString(),
                }],
            }),
        })
    );

    // Status do corte (usado em polling)
    await page.route(`**/api/generation/${CUT_ID}/status`, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                id: CUT_ID,
                status: 'completed',
                ...cutOverrides,
            }),
        })
    );

    // Audio URL do corte
    await page.route(`**/api/generation/${CUT_ID}/audio`, route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ url: 'https://r2.example.com/audio/cut.wav' }),
        })
    );
}

// ===========================================================================
// Cenário 1 — Notação já disponível na cloud
// ===========================================================================

test.describe('Cenário 1: Notação carregada da cloud', () => {
    test('deve renderizar iframe da partitura quando partitura_storage_key existe', async ({ page }) => {
        // Arrange
        await mockAuth(page);
        await mockAudioDetailBase(page, {
            partitura_status: 'completed',
            partitura_storage_key: `partitura/${CUT_ID}.pdf`,
        });

        // Mock GET presigned URL da partitura
        await page.route(`**/api/generation/${CUT_ID}/partitura`, async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ url: PARTITURA_URL }),
                });
            } else {
                await route.continue();
            }
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);

        // Act — selecionar o corte
        await audioPage.selectFirstCut();

        // Assert — iframe com a partitura deve aparecer automaticamente
        await audioPage.waitForPartituraIframe();
        const iframe = page.locator('iframe[title="Partitura"], iframe[title="Score"]').first();
        await expect(iframe).toHaveAttribute('src', PARTITURA_URL);
    });

    test('deve renderizar iframe da tablatura quando tablatura_storage_key existe', async ({ page }) => {
        // Arrange
        await mockAuth(page);
        await mockAudioDetailBase(page, {
            tablatura_status: 'completed',
            tablatura_storage_key: `tablature/${CUT_ID}.pdf`,
        });

        await page.route(`**/api/generation/${CUT_ID}/tablature`, async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200,
                    contentType: 'application/json',
                    body: JSON.stringify({ url: TABLATURA_URL }),
                });
            } else {
                await route.continue();
            }
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);
        await audioPage.selectFirstCut();

        // Assert
        await audioPage.waitForTablaturaIframe();
        const iframe = page.locator('iframe[title="Tablatura"], iframe[title="Tablature"]').first();
        await expect(iframe).toHaveAttribute('src', TABLATURA_URL);
    });

    test('deve mostrar botão "Regerar" ao lado do Download quando notação já existe', async ({ page }) => {
        // Arrange
        await mockAuth(page);
        await mockAudioDetailBase(page, {
            partitura_status: 'completed',
            partitura_storage_key: `partitura/${CUT_ID}.pdf`,
        });

        await page.route(`**/api/generation/${CUT_ID}/partitura`, async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200, contentType: 'application/json',
                    body: JSON.stringify({ url: PARTITURA_URL }),
                });
            } else { await route.continue(); }
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);
        await audioPage.selectFirstCut();
        await audioPage.waitForPartituraIframe();

        // Assert — botão Regerar visível na secção de partitura
        const regenerateBtn = page.locator('.cut-action-pdf-actions button')
            .filter({ hasText: /Regerar|Regenerate/i })
            .first();
        await expect(regenerateBtn).toBeVisible();
    });

    test('não deve mostrar botão "Regerar" quando notação ainda não foi gerada', async ({ page }) => {
        // Arrange — sem notação (idle)
        await mockAuth(page);
        await mockAudioDetailBase(page);

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);
        await audioPage.selectFirstCut();

        // Assert — botão Regerar não existe
        const regenerateBtn = page.locator('button').filter({ hasText: /Regerar|Regenerate/i });
        await expect(regenerateBtn).toHaveCount(0);
    });
});

// ===========================================================================
// Cenário 2 — Regerar: POST fire-and-forget + polling até completed
// ===========================================================================

test.describe('Cenário 2: Fluxo de regerar notação', () => {
    test('deve mostrar spinner após clicar em "Gerar Partitura"', async ({ page }) => {
        // Arrange — notação ainda não pedida (idle)
        await mockAuth(page);
        await mockAudioDetailBase(page);

        // Flag (não contador) accionada pelo POST — imune ao duplo efeito
        // inicial do <React.StrictMode> em dev, que dispararia um contador de
        // chamadas antes mesmo do clique do teste.
        let requested = false;

        // POST → 202 com status pending
        await page.route(`**/api/generation/${CUT_ID}/partitura`, async route => {
            if (route.request().method() === 'POST') {
                requested = true;
                await route.fulfill({
                    status: 202,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: CUT_ID,
                        status: 'completed',
                        partitura_status: 'pending',
                        partitura_storage_key: null,
                    }),
                });
            } else { await route.fallback(); }
        });

        // Sobrepõe o mock estático de mockAudioDetailBase: reflecte o POST
        // acima nas leituras seguintes de /cuts (refresh do hook pai).
        await page.route(`**/api/generation/${GEN_ID}/cuts`, async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    generations: [{
                        id: CUT_ID, status: 'completed',
                        parent_generation_id: GEN_ID,
                        prompt: 'Corte de teste',
                        audio_storage_key: `generations/cut_${CUT_ID}.wav`,
                        partitura_status: requested ? 'pending' : null,
                        partitura_storage_key: null,
                        tablatura_status: null, tablatura_storage_key: null,
                    }],
                }),
            });
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);
        await audioPage.selectFirstCut();

        // Act — clicar em "Gerar Partitura"
        const generateBtn = page.locator('button').filter({ hasText: /Gerar Partitura|Generate Score/i });
        await generateBtn.click();

        // Assert — spinner de "a gerar" aparece
        await audioPage.waitForGeneratingSpinner();
        const spinner = page.locator('text=/a gerar|generating/i').first();
        await expect(spinner).toBeVisible();
    });

    test('deve transitar para iframe quando polling retorna completed', async ({ page }) => {
        // Arrange — partimos de idle; POST muda para pending; polling retorna completed
        await mockAuth(page);
        await mockAudioDetailBase(page);

        // Contador de polls DEPOIS do pedido (não de todas as chamadas a
        // /cuts) — só começa a incrementar quando o POST realmente disparar.
        // Um contador "cru" seria consumido pelo duplo efeito inicial do
        // <React.StrictMode> em dev (monta → desmonta → monta), que faz
        // useAudioGenerations carregar a árvore duas vezes antes de o
        // teste sequer clicar em nada — fazendo a UI já aparecer 'completed'
        // antes do clique e o botão "Gerar Partitura" nunca ser encontrado.
        let requested = false;
        let pollsAfterRequest = 0;

        // POST dispara o job
        await page.route(`**/api/generation/${CUT_ID}/partitura`, async route => {
            if (route.request().method() === 'POST') {
                requested = true;
                await route.fulfill({
                    status: 202,
                    contentType: 'application/json',
                    body: JSON.stringify({
                        id: CUT_ID, status: 'completed',
                        partitura_status: 'pending', partitura_storage_key: null,
                    }),
                });
            } else if (route.request().method() === 'GET') {
                // Presigned URL (chamado quando completed)
                await route.fulfill({
                    status: 200, contentType: 'application/json',
                    body: JSON.stringify({ url: PARTITURA_URL }),
                });
            } else { await route.fallback(); }
        });

        // Polling: enquanto não pedido → idle; 1.ª leitura após o pedido →
        // pending; leituras seguintes → completed com chave.
        await page.route(`**/api/generation/${GEN_ID}/cuts`, async route => {
            let partitura_status: string | null = null;
            let partitura_storage_key: string | null = null;
            if (requested) {
                pollsAfterRequest++;
                partitura_status = pollsAfterRequest <= 1 ? 'pending' : 'completed';
                partitura_storage_key = pollsAfterRequest <= 1 ? null : `partitura/${CUT_ID}.pdf`;
            }
            await route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({
                    generations: [{
                        id: CUT_ID, status: 'completed',
                        parent_generation_id: GEN_ID,
                        prompt: 'Corte de teste',
                        audio_storage_key: `generations/cut_${CUT_ID}.wav`,
                        partitura_status, partitura_storage_key,
                        tablatura_status: null, tablatura_storage_key: null,
                    }],
                }),
            });
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);
        await audioPage.selectFirstCut();

        // Act
        const generateBtn = page.locator('button').filter({ hasText: /Gerar Partitura|Generate Score/i });
        await generateBtn.click();

        // Assert — eventualmente o iframe aparece (polling traz completed)
        await audioPage.waitForPartituraIframe(20_000);
        const iframe = page.locator('iframe[title="Partitura"], iframe[title="Score"]').first();
        await expect(iframe).toHaveAttribute('src', PARTITURA_URL);
    });

    test('deve reenfileirar ao clicar em "Regerar" e mostrar spinner', async ({ page }) => {
        // Arrange — notação já completed
        await mockAuth(page);
        await mockAudioDetailBase(page, {
            partitura_status: 'completed',
            partitura_storage_key: `partitura/${CUT_ID}.pdf`,
        });

        // Flag (não contador) accionada pelo POST de "Regerar" — imune ao
        // duplo efeito inicial do <React.StrictMode> em dev.
        let regenerateRequested = false;

        // GET → URL inicial; POST → 202 pending (regerar)
        await page.route(`**/api/generation/${CUT_ID}/partitura`, async route => {
            if (route.request().method() === 'GET') {
                await route.fulfill({
                    status: 200, contentType: 'application/json',
                    body: JSON.stringify({ url: PARTITURA_URL }),
                });
            } else if (route.request().method() === 'POST') {
                regenerateRequested = true;
                await route.fulfill({
                    status: 202, contentType: 'application/json',
                    body: JSON.stringify({
                        id: CUT_ID, status: 'completed',
                        partitura_status: 'pending', partitura_storage_key: null,
                    }),
                });
            } else { await route.fallback(); }
        });

        // Sobrepõe o mock estático de mockAudioDetailBase: reflecte o clique
        // em "Regerar" (POST acima) nas leituras seguintes de /cuts.
        await page.route(`**/api/generation/${GEN_ID}/cuts`, async route => {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    generations: [{
                        id: CUT_ID, status: 'completed',
                        parent_generation_id: GEN_ID,
                        prompt: 'Corte de teste',
                        audio_storage_key: `generations/cut_${CUT_ID}.wav`,
                        partitura_status: regenerateRequested ? 'pending' : 'completed',
                        partitura_storage_key: regenerateRequested ? null : `partitura/${CUT_ID}.pdf`,
                        tablatura_status: null, tablatura_storage_key: null,
                    }],
                }),
            });
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);
        await audioPage.selectFirstCut();
        await audioPage.waitForPartituraIframe();

        // Act — clicar em Regerar
        const regenerateBtn = page.locator('.cut-action-pdf-actions button')
            .filter({ hasText: /Regerar|Regenerate/i })
            .first();
        await regenerateBtn.click();

        // Assert — spinner aparece (status voltou a pending)
        await audioPage.waitForGeneratingSpinner();
    });
});
