import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { translations } from '../i18n/translations';
import type { Language, Translations } from '../i18n/translations';

/* -------------------------------------------------------------------------- */
/*  Tipos                                                                       */
/* -------------------------------------------------------------------------- */

interface LanguageContextValue {
    language: Language;
    t: Translations;
    toggleLanguage: () => void;
}

/* -------------------------------------------------------------------------- */
/*  Helpers                                                                     */
/* -------------------------------------------------------------------------- */

const STORAGE_KEY = 'music-ai-language';

function getStoredLanguage(): Language {
    try {
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored === 'pt' || stored === 'en') return stored;
    } catch {
        // localStorage indisponível
    }
    return 'pt';
}

/* -------------------------------------------------------------------------- */
/*  Context                                                                     */
/* -------------------------------------------------------------------------- */

const LanguageContext = createContext<LanguageContextValue | null>(null);

/* -------------------------------------------------------------------------- */
/*  Provider                                                                    */
/* -------------------------------------------------------------------------- */

export function LanguageProvider({ children }: { children: React.ReactNode }) {
    const [language, setLanguage] = useState<Language>(getStoredLanguage);

    // Aplica o atributo lang no <html> e persiste a escolha
    useEffect(() => {
        document.documentElement.setAttribute('lang', language);
        try {
            localStorage.setItem(STORAGE_KEY, language);
        } catch {
            // sem acesso ao localStorage
        }
    }, [language]);

    const toggleLanguage = useCallback(() => {
        setLanguage(l => (l === 'pt' ? 'en' : 'pt'));
    }, []);

    const t = translations[language];

    return (
        <LanguageContext.Provider value={{ language, t, toggleLanguage }}>
            {children}
        </LanguageContext.Provider>
    );
}

/* -------------------------------------------------------------------------- */
/*  Hook de consumo                                                             */
/* -------------------------------------------------------------------------- */

export function useLanguageContext(): LanguageContextValue {
    const ctx = useContext(LanguageContext);
    if (!ctx) {
        throw new Error('useLanguageContext deve ser usado dentro de <LanguageProvider>');
    }
    return ctx;
}

export default LanguageContext;
