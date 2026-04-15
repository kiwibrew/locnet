import { Text } from '../form/Intl';
import styles from './Header.module.css';
import { IframeModalButton } from './IFrameModalButton';
import { LanguagePicker } from './LanguagePicker';

export const Header = () => {
  return (
    <header>
      <nav className={styles.topNav}>
        <div className={styles.topNavFirst}>
          <h1 className={styles.pageTitle}>
            <Text intlId="banner" />
          </h1>
          <LanguagePicker />
        </div>
        <ul className={styles.navMenu}>
          <li>
            <IframeModalButton url="/qsg" dialogHeader="Quick Start Guide">
              Quick Start Guide
            </IframeModalButton>
          </li>
          <li>
            <IframeModalButton
              url="/documentation"
              dialogHeader="Documentation"
            >
              Documentation
            </IframeModalButton>
          </li>
        </ul>
      </nav>
    </header>
  );
};
