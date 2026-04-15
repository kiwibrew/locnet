import { useCallback, type ChangeEvent } from 'react';
import { useIntl, langsEntries, type IntlLang } from '../form/Intl.utils';
import styles from './LanguagePicker.module.css';

export const LanguagePicker = () => {
  const { lang, setLang } = useIntl();
  const handleChange = useCallback(
    (e: ChangeEvent<HTMLSelectElement>) => {
      const { target } = e;
      if (!(target instanceof HTMLSelectElement)) {
        throw Error('expected <select>');
      }
      setLang(target.value as IntlLang);
    },
    [setLang],
  );
  return (
    <div className={styles.container}>
      <label className={styles.label}>
        <Globe />
        <select value={lang} onChange={handleChange} className={styles.select}>
          {langsEntries.map(([langKey, name]) => {
            return <option value={langKey}>{name}</option>;
          })}
        </select>
      </label>
    </div>
  );
};

const Globe = () => {
  // public domain icon from https://commons.wikimedia.org/wiki/File:Globe_icon.svg
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="17"
      height="17"
      viewBox="0 0 420 420"
      stroke="#000"
      fill="none"
      aria-label="Choose language"
      className={styles.globe}
    >
      <path stroke-width="26" d="M209,15a195,195 0 1,0 2,0z" />
      <path
        stroke-width="18"
        d="m210,15v390m195-195H15M59,90a260,260 0 0,0 302,0 m0,240 a260,260 0 0,0-302,0M195,20a250,250 0 0,0 0,382 m30,0 a250,250 0 0,0 0-382"
      />
    </svg>
  );
};
