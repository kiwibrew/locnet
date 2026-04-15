import { useEffect } from 'react';

export const useScrollBarWidth = (): void => {
  useEffect(() => {
    const updateScrollbarWidth = () => {
      document.body.style.setProperty(
        '--scrollbar-width',
        window.innerWidth - document.documentElement.clientWidth + 'px',
      );
    };

    window.addEventListener('resize', updateScrollbarWidth, false);
    document.addEventListener('DOMContentLoaded', updateScrollbarWidth, false);
    window.addEventListener('load', updateScrollbarWidth);
    const timer = window.setInterval(updateScrollbarWidth, 1000);

    return () => {
      window.removeEventListener('resize', updateScrollbarWidth);
      document.removeEventListener('DOMContentLoaded', updateScrollbarWidth);
      window.removeEventListener('load', updateScrollbarWidth);

      if (timer) {
        clearInterval(timer);
      }
    };
  }, []);
};
