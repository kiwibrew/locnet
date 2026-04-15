import { useEffect, useRef, useState, type PropsWithChildren } from 'react';
import { debounce } from 'lodash-es';
import styles from './ScrollHorizontally.module.css';

// eslint-disable-next-line
type Props = PropsWithChildren<{}>;

const BUFFER_PX = 5;

export const ScrollHorizontally = ({ children }: Props) => {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  useEffect(() => {
    const { current: scrollContainerElement } = scrollContainerRef;
    if (!scrollContainerElement) {
      console.error('expected to find scroll container ref');
      return;
    }

    const updateScrollHint = () => {
      const { current: scrollContainerElement } = scrollContainerRef;
      if (!scrollContainerElement) {
        console.error('expected to find scroll container ref');
        return;
      }
      if (!(scrollContainerElement instanceof HTMLElement)) {
        throw Error("Scroll container isn't HTML Element. This is a bug.");
      }
      setCanScrollLeft(() => scrollContainerElement.scrollLeft > BUFFER_PX);
      setCanScrollRight(
        () =>
          scrollContainerElement.scrollLeft +
            scrollContainerElement.offsetWidth <
          scrollContainerElement.scrollWidth - BUFFER_PX,
      );
    };

    const debouncedUpdateScrollHint = debounce(updateScrollHint, 100);

    window.addEventListener('resize', debouncedUpdateScrollHint);
    const observer = new ResizeObserver(debouncedUpdateScrollHint);
    observer.observe(scrollContainerElement);

    return () => {
      window.removeEventListener('resize', debouncedUpdateScrollHint);
      observer.disconnect();
    };
  }, []);

  return (
    <div
      ref={scrollContainerRef}
      className={[
        styles.container,
        canScrollLeft && !canScrollRight ? styles.canScrollLeft : '',
        canScrollRight && !canScrollLeft ? styles.canScrollRight : '',
        canScrollRight && canScrollLeft ? styles.canScrollBoth : '',
      ].join(' ')}
    >
      {children}
    </div>
  );
};
