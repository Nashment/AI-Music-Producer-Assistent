import { test, expect } from '@playwright/test';
import { AudioDetailPage } from '../../pages/AudioDetailPage';

// ---------------------------------------------------------------------------
// UUIDs estáticos
// ---------------------------------------------------------------------------
const PROJECT_ID = 'aaaaaaaa-0000-0000-0000-000000000001';
const AUDIO_ID   = 'bbbbbbbb-0000-0000-0000-000000000002';
const GEN_ID     = 'cccccccc-0000-0000-0000-000000000003';
const CUT_ID     = 'dddddddd-0000-0000-0000-000000000004';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function mockAuth(page: import('@playwright/test').Page) {
    // Rota real é /users/me (plural) — ver src/services/request.ts.
    await page.route('**/api/users/me', route =>
        route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ id: 'user-001', username: 'testuser' }),
        })
    );
    // Chave real em localStorage é 'music_ai.access_token' — ver
    // src/utils/auth.ts STORAGE_KEY. Com a chave errada o ProtectedRoute
    // redirecciona sempre para /login antes de qualquer teste correr.
    await page.addInitScript(() => {
        localStorage.setItem('music_ai.access_token', 'fake.jwt.token');
    });
}

/** Monta a árvore com 1 geração root + 1 corte. */
async function mockTreeWithGenerationAndCut(
    page: import('@playwright/test').Page,
    {
        includeGen = true,
        includeCut = true,
    }: { includeGen?: boolean; includeCut?: boolean } = {}
) {
    await page.route(`**/api/audio/analysis/${AUDIO_ID}`, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({
                id: AUDIO_ID, storage_key: 'audio/test.wav',
                duration: 30.0, sample_rate: 44100, bpm: 120,
                key: 'C major', time_signature: '4/4',
            }),
        })
    );

    await page.route(`**/api/audio/${AUDIO_ID}`, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ url: 'https://r2.example.com/audio/test.wav' }),
        })
    );

    const generations = includeGen ? [{
        id: GEN_ID, status: 'completed',
        project_id: PROJECT_ID, audio_file_id: AUDIO_ID,
        prompt: 'Guitarra clássica', instrument: 'guitarra',
        audio_storage_key: `generations/${GEN_ID}.mp3`,
        partitura_status: null, tablatura_status: null,
        partitura_storage_key: null, tablatura_storage_key: null,
        created_at: new Date().toISOString(),
    }] : [];

    await page.route(`**/api/generation/by-audio/${AUDIO_ID}`, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ generations }),
        })
    );

    const cuts = includeCut ? [{
        id: CUT_ID, status: 'completed',
        project_id: PROJECT_ID, audio_file_id: AUDIO_ID,
        parent_generation_id: GEN_ID,
        prompt: `Corte de ${GEN_ID} (0.00s-15.00s)`,
        instrument: 'guitarra',
        audio_storage_key: `generations/cut_${CUT_ID}.wav`,
        partitura_status: null, tablatura_status: null,
        partitura_storage_key: null, tablatura_storage_key: null,
        created_at: new Date().toISOString(),
    }] : [];

    await page.route(`**/api/generation/${GEN_ID}/cuts`, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ generations: cuts }),
        })
    );

    await page.route(`**/api/generation/${CUT_ID}/audio`, route =>
        route.fulfill({
            status: 200, contentType: 'application/json',
            body: JSON.stringify({ url: 'https://r2.example.com/audio/cut.wav' }),
        })
    );
}

// ===========================================================================
// Cenário 3 — Eliminação de geração e corte
// ===========================================================================

test.describe('Cenário 3: Eliminar geração de áudio', () => {

    test('deve mostrar modal de confirmação ao clicar no botão eliminar de uma geração', async ({ page }) => {
        // Arrange
        await mockAuth(page);
        await mockTreeWithGenerationAndCut(page);

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);

        // Act — hover e clicar no botão 🗑 da geração root
        await audioPage.clickDeleteOnRoot(0);

        // Assert — modal abre com título correto
        await expect(audioPage.confirmModal).toBeVisible();
        await expect(audioPage.confirmModalTitle).toContainText(
            /Eliminar permanentemente|Delete permanently/i
        );
    });

    test('deve cancelar a eliminação ao clicar em "Cancelar"', async ({ page }) => {
        // Arrange
        await mockAuth(page);
        await mockTreeWithGenerationAndCut(page);

        let deleteWasCalled = false;
        await page.route(`**/api/generation/${GEN_ID}`, route => {
            if (route.request().method() === 'DELETE') {
                deleteWasCalled = true;
                route.fulfill({ status: 204 });
            } else {
                route.continue();
            }
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);
        await audioPage.clickDeleteOnRoot(0);
        await expect(audioPage.confirmModal).toBeVisible();

        // Act — cancelar
        await audioPage.cancelBtn.click();

        // Assert — modal fecha; API não foi chamada; geração permanece na lista
        await expect(audioPage.confirmModal).not.toBeVisible();
        expect(deleteWasCalled).toBe(false);
        await expect(audioPage.genTreeRoots).toHaveCount(1);
    });

    test('deve remover a geração da lista após confirmar eliminação', async ({ page }) => {
        // Arrange
        await mockAuth(page);
        await mockTreeWithGenerationAndCut(page);

        // Flag (não contador) accionada pelo DELETE — imune a chamadas GET
        // extra que aconteçam antes do utilizador confirmar a eliminação
        // (ex.: o duplo efeito inicial do <React.StrictMode> em dev).
        let deleted = false;

        // Mock DELETE → 204
        await page.route(`**/api/generation/${GEN_ID}`, route => {
            if (route.request().method() === 'DELETE') {
                deleted = true;
                route.fulfill({ status: 204 });
            } else { route.continue(); }
        });

        // Após delete, listagem não inclui a geração eliminada
        await page.route(`**/api/generation/by-audio/${AUDIO_ID}`, route => {
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({
                    generations: deleted
                        ? [] // após delete: lista vazia
                        : [{ // antes do delete
                            id: GEN_ID, status: 'completed',
                            project_id: PROJECT_ID, audio_file_id: AUDIO_ID,
                            prompt: 'Guitarra clássica', instrument: 'guitarra',
                            audio_storage_key: `generations/${GEN_ID}.mp3`,
                            partitura_status: null, tablatura_status: null,
                            partitura_storage_key: null, tablatura_storage_key: null,
                          }],
                }),
            });
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);

        // Confirmar que há 1 geração inicialmente
        await expect(audioPage.genTreeRoots).toHaveCount(1);

        // Act — abrir modal e confirmar
        await audioPage.clickDeleteOnRoot(0);
        await expect(audioPage.confirmModal).toBeVisible();
        await audioPage.confirmBtn.click();

        // Assert — modal fecha e lista fica vazia
        await expect(audioPage.confirmModal).not.toBeVisible();
        await expect(audioPage.genTreeRoots).toHaveCount(0, { timeout: 8_000 });
    });

    test('deve remover um corte sem afectar a geração pai', async ({ page }) => {
        // Arrange
        await mockAuth(page);
        await mockTreeWithGenerationAndCut(page);

        // Flag (não contador) accionada pelo DELETE do corte — um contador
        // de chamadas a /cuts seria frágil a qualquer fetch extra que
        // aconteça antes do utilizador confirmar a eliminação (ex.: o duplo
        // efeito inicial do <React.StrictMode> em dev, que faz
        // useAudioGenerations carregar a árvore mais do que uma vez).
        let cutDeleted = false;

        await page.route(`**/api/generation/${CUT_ID}`, route => {
            if (route.request().method() === 'DELETE') {
                cutDeleted = true;
                route.fulfill({ status: 204 });
            } else { route.continue(); }
        });

        // Após delete do corte, cuts ficam vazios mas geração permanece
        await page.route(`**/api/generation/${GEN_ID}/cuts`, route => {
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({
                    generations: cutDeleted
                        ? []
                        : [{
                            id: CUT_ID, status: 'completed',
                            parent_generation_id: GEN_ID,
                            prompt: 'Corte de teste',
                            audio_storage_key: `generations/cut_${CUT_ID}.wav`,
                            partitura_status: null, tablatura_status: null,
                            partitura_storage_key: null, tablatura_storage_key: null,
                          }],
                }),
            });
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);

        // Act — eliminar o corte
        await audioPage.clickDeleteOnCut(0);
        await expect(audioPage.confirmModal).toBeVisible();
        await audioPage.confirmBtn.click();

        // Assert — corte desaparece mas geração root permanece
        await expect(audioPage.confirmModal).not.toBeVisible();
        await expect(audioPage.genTreeRoots).toHaveCount(1, { timeout: 8_000 });
        const cutItems = page.locator('.gen-tree-item-cut');
        await expect(cutItems).toHaveCount(0, { timeout: 8_000 });
    });

    test('deve limpar a seleção se o item eliminado estava seleccionado', async ({ page }) => {
        // Arrange — selecionar o corte antes de o eliminar
        await mockAuth(page);
        await mockTreeWithGenerationAndCut(page);

        // Flag (não contador) accionada pelo DELETE do corte. A versão
        // original devolvia sempre `generations: []`, o que impedia o corte
        // de sequer aparecer para ser seleccionado — o teste nunca podia ter
        // passado. Aqui só fica vazio depois do DELETE de facto acontecer.
        let cutDeleted = false;

        await page.route(`**/api/generation/${CUT_ID}`, route => {
            if (route.request().method() === 'DELETE') {
                cutDeleted = true;
                route.fulfill({ status: 204 });
            } else { route.continue(); }
        });

        await page.route(`**/api/generation/${GEN_ID}/cuts`, async route => {
            await route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({
                    generations: cutDeleted ? [] : [{
                        id: CUT_ID, status: 'completed',
                        parent_generation_id: GEN_ID,
                        prompt: 'Corte de teste',
                        audio_storage_key: `generations/cut_${CUT_ID}.wav`,
                        partitura_status: null, tablatura_status: null,
                        partitura_storage_key: null, tablatura_storage_key: null,
                    }],
                }),
            });
        });

        await page.route(`**/api/generation/${CUT_ID}/audio`, route =>
            route.fulfill({
                status: 200, contentType: 'application/json',
                body: JSON.stringify({ url: 'https://r2.example.com/audio/cut.wav' }),
            })
        );

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);

        // Seleccionar o corte (painel direito mostra CutActionPanel)
        await audioPage.selectFirstCut();
        await expect(audioPage.cutActionPanel).toBeVisible();

        // Act — eliminar o corte seleccionado
        await audioPage.clickDeleteOnCut(0);
        await audioPage.confirmBtn.click();

        // Assert — painel do corte desaparece (seleção limpada → volta ao estado idle)
        await expect(audioPage.cutActionPanel).not.toBeVisible({ timeout: 8_000 });
    });

    test('não deve chamar DELETE ao clicar no botão de seleção da geração', async ({ page }) => {
        // Verifica que stopPropagation funciona: clicar no item não dispara delete
        await mockAuth(page);
        await mockTreeWithGenerationAndCut(page);

        let deleteWasCalled = false;
        await page.route(`**/api/generation/**`, route => {
            if (route.request().method() === 'DELETE') {
                deleteWasCalled = true;
                route.fulfill({ status: 204 });
            } else {
                // IMPORTANTE: route.fallback() (não route.continue()) — isto
                // devolve o pedido aos handlers mais específicos já
                // registados por mockTreeWithGenerationAndCut (by-audio,
                // cuts, audio). route.continue() deixava o pedido escapar
                // para a rede real, que o Vite tentava fazer proxy para um
                // backend que não está a correr (ECONNREFUSED) — a árvore
                // nunca carregava e o teste ficava preso 30s à espera de
                // '.gen-tree-item'.
                route.fallback();
            }
        });

        const audioPage = new AudioDetailPage(page);
        await audioPage.goto(PROJECT_ID, AUDIO_ID);

        // Act — clicar no botão de seleção (não no 🗑)
        const selBtn = page.locator('.gen-tree-item').first();
        // A geração está disabled (só pode ser seleccionada quando completed,
        // mas o click não deve disparar delete)
        await selBtn.click({ force: true });

        // Assert — DELETE nunca foi chamado
        await page.waitForTimeout(500);
        expect(deleteWasCalled).toBe(false);
        await expect(audioPage.confirmModal).not.toBeVisible();
    });
});
