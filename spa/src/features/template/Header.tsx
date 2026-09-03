import { Text } from '../form/Intl';
import styles from './Header.module.css';
import { IframeModalButton } from './IFrameModalButton';
import { LanguagePicker } from './LanguagePicker';
import { ModelFileControls } from '../locnet/ModelFileControls';
import { getCsrfToken, getCurrentUser } from '../auth/session';

export const Header = () => {
  const currentUser = getCurrentUser();
  const csrfToken = getCsrfToken();

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
              Quick Start
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
          <li>
            <IframeModalButton url="/faq" dialogHeader="FAQ">
              FAQ
            </IframeModalButton>
          </li>
          <ModelFileControls />
          {currentUser.api_access_enabled && !currentUser.is_admin ? (
            <li>
              <a href="/docs">API documentation</a>
            </li>
          ) : null}
          {currentUser.is_admin ? (
            <li>
              <a href="http://127.0.0.1:8000/manage-users">Admin Panel</a>
            </li>
          ) : null}
          <li>
            <form method="post" action="/logout">
              <input type="hidden" name="csrf_token" value={csrfToken} />
              <button type="submit">Sign out ({currentUser.email})</button>
            </form>
          </li>
        </ul>
      </nav>
    </header>
  );
};
