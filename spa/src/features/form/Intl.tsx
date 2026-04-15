import { useCallback, useState, type PropsWithChildren } from 'react';
import {
  getDefaultLang,
  IntlContext,
  setLocalStorageLang,
  langRef,
  useIntlIdOrText,
  type IntlLang,
} from './Intl.utils';

type Props = PropsWithChildren;

export const IntlProvider = ({ children }: Props) => {
  const [lang, setLangState] = useState<IntlLang>(getDefaultLang());
  const setLang = useCallback(
    (lang: IntlLang) => {
      setLangState(lang);
      setLocalStorageLang(lang);
      langRef.current = lang;
    },
    [setLangState],
  );
  return (
    <IntlContext.Provider
      value={{
        lang,
        setLang,
      }}
    >
      {children}
    </IntlContext.Provider>
  );
};

type TextProps = {
  intlId?: string;
  text?: string;
};

export const Text = ({ intlId, text }: TextProps) => {
  return <>{useIntlIdOrText(intlId, text)}</>;
};
