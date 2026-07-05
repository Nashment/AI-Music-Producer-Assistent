import { type Page, type Locator, expect } from '@playwright/test';

/**
 * Page Object para /projects/:projectId/audio/:audioId.
 *
 * Encapsula todos os seletores e ações da página de detalhe de áudio,
 * incluindo a árvore de gerações/cortes e os painéis de notação.
 */
export class AudioDetailPage {
    readonly page: Page;

    // Layout principal
    readonly audioWorkspace:    Locator;
    readonly generationTree:    Locator;

    // Árvore de gerações
    readonly genTreeRoots:      Locator;
    readonly genTreeDeleteBtns: Locator;

    // Painel de notação (CutActionPanel)
    readonly cutActionPanel:    Locator;
    readonly partituraSection:  Locator;
    readonly tablaturaSection:  Locator;

    // Modal de confirmação
    readonly confirmModal:      Locator;
    readonly confirmModalTitle: Locator;
    readonly confirmBtn:        Locator;
    readonly cancelBtn:         Locator;

    // Spinner genérico
    readonly spinner:           Locator;

    constructor(page: Page) {
        this.page = page;

        this.audioWorkspace    = page.locator('.audio-workspace');
        this.generationTree    = page.locator('.gen-tree');
        this.genTreeRoots      = page.locator('.gen-tree-root');
        this.genTreeDeleteBtns = page.locator('.gen-tree-delete');

        this.cutActionPanel    = page.locator('.cut-action-panel');
        this.partituraSection  = page.locator('.cut-action-pdf, .cut-action-notation').first();
        this.tablaturaSection  = page.locator('.cut-action-pdf, .cut-action-notation').nth(1);

        this.confirmModal      = page.locator('[role="dialog"]');
        this.confirmModalTitle = page.locator('[role="dialog"] h2');
        this.confirmBtn        = page.locator('[role="dialog"] .btn-danger');
        this.cancelBtn         = page.locator('[role="dialog"] .btn-secondary');

        this.spinner           = page.locator('[class*="spinner"], [aria-label*="gerar"], [aria-label*="Generat"]').first();
    }

    async goto(projectId: string, audioId: string) {
        await this.page.goto(`/projects/${projectId}/audio/${audioId}`);
        await this.audioWorkspace.waitFor({ state: 'visible', timeout: 10_000 });
    }

    /** Clica no primeiro corte da árvore (nível 2). */
    async selectFirstCut() {
        const cutBtn = this.page.locator('.gen-tree-item-cut').first();
        await cutBtn.click();
        await this.cutActionPanel.waitFor({ state: 'visible', timeout: 5_000 });
    }

    /** Clica no botão 🗑 de uma geração root pelo índice (0-based). */
    async clickDeleteOnRoot(index = 0) {
        const row = this.page.locator('.gen-tree-root .gen-tree-row').nth(index);
        await row.hover();
        await row.locator('.gen-tree-delete').click();
    }

    /** Clica no botão 🗑 de um corte pelo índice (0-based). */
    async clickDeleteOnCut(index = 0) {
        const row = this.page.locator('.gen-tree-children .gen-tree-row').nth(index);
        await row.hover();
        await row.locator('.gen-tree-delete').click();
    }

    /** Devolve o texto do botão "Gerar Partitura / Regerar" da secção de partitura. */
    async getPartituraButtonText(): Promise<string> {
        return this.page
            .locator('.cut-action-notation button, .cut-action-pdf-actions button')
            .first()
            .innerText();
    }

    /** Aguarda que o iframe da partitura apareça (fase 'completed'). */
    async waitForPartituraIframe(timeout = 15_000) {
        await this.page
            .locator('iframe[title="Partitura"], iframe[title="Score"]')
            .waitFor({ state: 'visible', timeout });
    }

    /** Aguarda que o iframe da tablatura apareça (fase 'completed'). */
    async waitForTablaturaIframe(timeout = 15_000) {
        await this.page
            .locator('iframe[title="Tablatura"], iframe[title="Tablature"]')
            .waitFor({ state: 'visible', timeout });
    }

    /** Aguarda que o spinner de "a gerar" apareça. */
    async waitForGeneratingSpinner(timeout = 5_000) {
        await this.page
            .locator('text=/a gerar|generating/i')
            .first()
            .waitFor({ state: 'visible', timeout });
    }
}
