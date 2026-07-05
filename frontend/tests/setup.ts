/**
 * Setup global para testes Vitest (unit).
 * Limpa todos os mocks após cada teste — padrão AAA.
 */
import { afterEach, vi } from 'vitest';
// Regista os matchers de DOM (toBeInTheDocument, toHaveTextContent, etc.)
// no `expect` do Vitest. Sem isto, qualquer teste que use esses matchers
// falha com "Invalid Chai property: toBeInTheDocument", porque o Vitest
// usa Chai por baixo e não conhece esses matchers por si só.
import '@testing-library/jest-dom/vitest';

afterEach(() => {
    vi.clearAllMocks();
});
