import { createContext, useContext } from 'react';
import { getDomJson } from './domJson';
import { z } from 'zod';

export const LangSchema = z.union([z.literal('en'), z.literal('es')]);

export type IntlLang = z.infer<typeof LangSchema>;

export const langs = {
  en: 'English',
  es: 'Español',
} as Record<IntlLang, string>;

export const langsEntries = Object.entries(langs) as [IntlLang, string][];

const DEFAULT_LANG: IntlLang = 'en';

const localStorageKey = 'locnet_lang';

export const langKeys = Object.keys(langs) as IntlLang[];

export const setLocalStorageLang = (langKey: IntlLang) => {
  try {
    window.localStorage.setItem(localStorageKey, langKey);
  } catch (e) {
    console.error(e);
  }
};

export const getDefaultLang = (): IntlLang => {
  // Saved user preference in localStorage
  try {
    const result = window.localStorage.getItem(localStorageKey);
    if (result && langKeys.includes(result as IntlLang)) {
      return result as IntlLang;
    }
  } catch (e) {
    console.error(e);
  }

  // browser language preference
  for (let i = 0; i < navigator.languages.length; i++) {
    const userPreferedLanguage = navigator.languages[i].toLowerCase();
    for (let langKeyIndex = 0; langKeyIndex < langKeys.length; langKeyIndex++) {
      const langKey = langKeys[langKeyIndex];
      const langKeyLower = langKey.toLowerCase();
      if (
        userPreferedLanguage === langKeyLower ||
        userPreferedLanguage.startsWith(`${langKeyLower}-`)
      ) {
        return langKey;
      }
    }
  }

  return DEFAULT_LANG;
};

export const IntlContext = createContext<{
  lang: IntlLang;
  setLang: (lang: IntlLang) => void;
} | null>(null);

type LangIntlIdLookup = Record<IntlLang, Record<string, string | undefined>>;

const getLangIntlIdLookup = () => {
  const TextSchema = z
    .object({ element: z.string(), en: z.string(), es: z.string() })
    .array();
  const textJson = getDomJson('text');
  const text = textJson ? TextSchema.parse(textJson) : [];
  return text.reduce(
    (acc, item) => {
      acc['en'][item.element] = item.en;
      acc['es'][item.element] = item.es;
      return acc;
    },
    { en: {}, es: {} } as LangIntlIdLookup,
  );
};

export const langIntlIdLookup = getLangIntlIdLookup();

export const langRef: { current: IntlLang } = {
  current: 'en',
};

/** Not a React hook */
export const getLang = () => langRef.current;

export const useIntl = () => {
  const val = useContext(IntlContext);
  if (!val) {
    throw Error('Expected useIntl to have context available');
  }
  return val;
};

export const useIntlIdOrText = (
  intlId: string | undefined,
  text: string | undefined,
): string | undefined => {
  const { lang } = useIntl();
  if (text) {
    return text;
  }
  if (intlId) {
    return (
      langIntlIdLookup[lang][intlId] ?? langIntlIdLookup[DEFAULT_LANG][intlId]
    );
  }
};
