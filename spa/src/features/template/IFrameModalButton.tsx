import styles from './IFrameModalButton.module.css';
import { useRef, type PropsWithChildren } from 'react';

type Props = PropsWithChildren<{
  url: string;
  dialogHeader: string;
}>;

export const IframeModalButton = ({ url, dialogHeader, children }: Props) => {
  const dialogRef = useRef<HTMLDialogElement | null>(null);

  const openModal = (e: React.MouseEvent<HTMLAnchorElement, MouseEvent>) => {
    e.preventDefault();
    if (!dialogRef.current) {
      console.log("didn't find dialog ref");
      return;
    }
    dialogRef.current.showModal();
  };

  const closeModal = (e: React.MouseEvent<HTMLButtonElement, MouseEvent>) => {
    e.preventDefault();
    if (!dialogRef.current) {
      console.log("didn't find dialog ref");
      return;
    }
    dialogRef.current.close();
    console.log(dialogRef.current.open);
  };

  return (
    <>
      <a href={url} onClick={openModal}>
        {children}
      </a>
      <dialog ref={dialogRef} className={styles.dialog}>
        <div className={styles.dialogHeader}>{dialogHeader}</div>
        <iframe src={url} className={styles.dialogIframe}></iframe>
        <button
          type="button"
          className={styles.dialogClose}
          onClick={closeModal}
        >
          &times;
        </button>
      </dialog>
    </>
  );
};
