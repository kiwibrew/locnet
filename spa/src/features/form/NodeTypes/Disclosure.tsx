import { z } from 'zod';
import { TiChevronRight } from 'react-icons/ti';
import { formPathJoin } from '../path';
import { FormNodeSchema } from '../base';
import { NodesSchema, type NodeProps } from '../node';
import { RenderNodes } from '../RenderNodes';
import { useCallback, useEffect, useRef } from 'react';
import { Text } from '../Intl';
import { useStaticFormTsContext } from '../FormProvider';
import styles from './Disclosure.module.css';

export const DisclosureSchema = FormNodeSchema.extend({
  type: z.literal('Disclosure'),
  isOpen: z.boolean().optional(),
  id: z.string().optional(),
  isButtonVisible: z.boolean().optional(),
  get children() {
    return NodesSchema;
  },
});

export type Disclosure = z.infer<typeof DisclosureSchema>;

type Props = NodeProps<Disclosure>;

export const RenderDisclosure = ({ node, formPath }: Props) => {
  const { useFormAndModel } = useStaticFormTsContext();
  const childrenPath = formPathJoin<Disclosure>(formPath, 'children');
  const isOpenPath = formPathJoin<Disclosure>(formPath, 'isOpen');
  const isButtonVisiblePath = formPathJoin<Disclosure>(
    formPath,
    'isButtonVisible',
  );

  const [isOpen, setIsOpen] = useFormAndModel(
    isOpenPath,
    undefined,
    node.isOpen ?? false,
    true
  );

  const [isButtonVisible] = useFormAndModel(
    isButtonVisiblePath,
    undefined,
    node.isButtonVisible === false ? false : true,
  );

  const handleToggle = useCallback(
    () => setIsOpen((prevValue) => !prevValue),
    [setIsOpen],
  );

  const childrenContainerRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const { current: childrenContainer } = childrenContainerRef;
    if (!childrenContainer) return;
    childrenContainer.addEventListener('focusin', () => {
      setIsOpen((prevIsOpen) => {
        const { activeElement } = document;

        if (
          // only scroll if we've just opened the disclosure
          prevIsOpen === false &&
          // only scroll if there's an element to scroll to
          activeElement
        ) {
          // scroll to current focused element
          // but do so after React rerenders
          setTimeout(() => {
            try {
              activeElement.scrollIntoView({
                block: 'center',
                inline: 'center',
              });
            } catch (e) {
              console.error("Internal error. Couldn't scroll to element", {
                activeElement,
              });
              console.error(e);
            }
          }, 50);
        }

        return true;
      });
    });
  }, [setIsOpen]);

  // Despite being a 'disclosure' widget we can't use <details>/<summary> because we need
  // children nodes to be navigable, so that their validation rules are included in the
  // native HTML form validation that we're using
  // So we'll render a toggle button instead
  return (
    <>
      {isButtonVisible && (
        <button
          type="button"
          className={styles.button}
          aria-pressed={isOpen}
          onClick={handleToggle}
        >
          <TiChevronRight
            className={[styles.arrow, isOpen ? styles.arrowIsOpen : ''].join(
              ' ',
            )}
          />
          <Text intlId={node.labelIntlId} text={node.labelText} />
        </button>
      )}
      <div
        className={[
          styles.children,
          isButtonVisible ? styles.childrenWithButtonVisible : '',
        ].join(' ')}
        style={{
          display: 'block',
          overflow: isOpen ? 'visible' : 'hidden',
          height: isOpen ? 'auto' : '0px',
        }}
        ref={childrenContainerRef}
        key={formPath}
        id={node.id}
      >
        <RenderNodes nodes={node.children} id={childrenPath} />
      </div>
    </>
  );
};
