/**
 * Testes unitários para src/utils/auth.ts.
 *
 * Cobre:
 *   - saveAuth / getAccessToken / getStoredUser / clearAuth / isAuthenticated
 *   - Uso das chaves reais de localStorage ('music_ai.access_token',
 *     'music_ai.current_user') — ver nota em frontend_test_suite_fixed.md
 *     sobre o bug de e2e causado por chaves erradas.
 *   - Robustez a JSON inválido em localStorage.
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
    saveAuth,
    getAccessToken,
    getStoredUser,
    clearAuth,
    isAuthenticated,
} from '../../../src/utils/auth';

const STORAGE_KEY = 'music_ai.access_token';
const USER_KEY = 'music_ai.current_user';

beforeEach(() => {
    localStorage.clear();
});

describe('saveAuth', () => {
    it('grava o token na chave real usada pelo resto da app', () => {
        saveAuth('token-abc', { id: 'u1', username: 'nash' });
        expect(localStorage.getItem(STORAGE_KEY)).toBe('token-abc');
    });

    it('grava o utilizador como JSON na chave real', () => {
        saveAuth('token-abc', { id: 'u1', username: 'nash' });
        expect(JSON.parse(localStorage.getItem(USER_KEY)!)).toEqual({ id: 'u1', username: 'nash' });
    });
});

describe('getAccessToken', () => {
    it('devolve o token gravado', () => {
        saveAuth('token-xyz', { id: 'u1', username: 'nash' });
        expect(getAccessToken()).toBe('token-xyz');
    });

    it('devolve null quando não há token', () => {
        expect(getAccessToken()).toBeNull();
    });
});

describe('getStoredUser', () => {
    it('devolve o utilizador gravado', () => {
        saveAuth('token-xyz', { id: 'u1', username: 'nash' });
        expect(getStoredUser()).toEqual({ id: 'u1', username: 'nash' });
    });

    it('devolve null quando não há utilizador gravado', () => {
        expect(getStoredUser()).toBeNull();
    });

    it('devolve null (sem lançar excepção) quando o JSON gravado é inválido', () => {
        localStorage.setItem(USER_KEY, '{not-valid-json');
        expect(getStoredUser()).toBeNull();
    });
});

describe('clearAuth', () => {
    it('remove token e utilizador', () => {
        saveAuth('token-xyz', { id: 'u1', username: 'nash' });
        clearAuth();
        expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
        expect(localStorage.getItem(USER_KEY)).toBeNull();
    });
});

describe('isAuthenticated', () => {
    it('devolve true quando há token', () => {
        saveAuth('token-xyz', { id: 'u1', username: 'nash' });
        expect(isAuthenticated()).toBe(true);
    });

    it('devolve false quando não há token', () => {
        expect(isAuthenticated()).toBe(false);
    });

    it('devolve false depois de clearAuth', () => {
        saveAuth('token-xyz', { id: 'u1', username: 'nash' });
        clearAuth();
        expect(isAuthenticated()).toBe(false);
    });
});
