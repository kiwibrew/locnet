import { type ImageType } from 'write-excel-file';
import { replaceNonNumberChars } from '../../utils/strings';

export type Cell = {
  type: 'string' | 'date' | 'number';
  value?: string | number;
  fontWeight?: 'bold';
};

export type Row = Cell[];

export type Image = ImageType<Blob>;

export type Sheet = {
  name: string;
  rows: Row[];
  images: Image[];
};

// Assumes landscape
const CANVAS_WIDTH = 700;
const CANVAS_HEIGHT = 500;

const BITMAP_MIME_TYPE = 'image/png';

export const getSheets = async (exportElm: HTMLElement) => {
  const canvgPromise = import('canvg').then((module) => module.Canvg);

  const sheetElements = Array.from(exportElm.querySelectorAll('[data-sheet]'));

  const sheetNames = sheetElements.map(
    (elm, index) =>
      elm.querySelector<HTMLElement>('[data-sheet-name]')?.innerText ??
      `Sheet ${index + 1}`,
  );

  const sheets = await Promise.all(
    sheetElements.map(async (sheetElement, index): Promise<Sheet> => {
      const name = sheetNames[index];
      const contentElement = sheetElement.querySelector('table, svg');
      if (!contentElement) {
        return {
          name,
          rows: [],
          images: [],
        };
      }

      const rows: Row[] = [];
      const images: Image[] = [];

      if (contentElement instanceof HTMLTableElement) {
        const tableElement = contentElement;

        const headerRow: Row = Array.from(
          // Note, assumes only a single thead tr
          tableElement.tHead?.querySelectorAll<HTMLElement>('td,th') ?? [],
        ).map((cell): Cell => {
          const isNumber = cell.querySelector('*[data-number]')
          const text = cell.innerText;
          return {
            type: isNumber ? 'number' : 'string',
            value: isNumber ? parseFloat(replaceNonNumberChars(text)) : text,
            fontWeight:
              cell.nodeName.toLowerCase() === 'th' ? 'bold' : undefined,
          };
        });
        rows.push(headerRow);
        const trElements = Array.from(
          tableElement
            .querySelector<HTMLElement>(
              // assumes a single tbody
              'tbody',
            )
            ?.querySelectorAll<HTMLElement>('tr') ?? [],
        );

        rows.push(
          ...trElements.map((tr) => {
            const cells = Array.from(
              tr.querySelectorAll<HTMLElement>('td,th') ?? [],
            );

            return cells.map((cell): Cell => {
              const isNumber = cell.querySelector('*[data-number]')
              const text = cell.innerText;
              return {
                type: isNumber ? 'number' : 'string',
                value: isNumber
                  ? parseFloat(replaceNonNumberChars(text))
                  : text,
                fontWeight:
                  cell.nodeName.toLowerCase() === 'th' ? 'bold' : undefined,
              };
            });
          }),
        );
      } else if (contentElement instanceof SVGElement) {
        console.log('found SVG!');
        const svgString = contentElement.outerHTML;
        const canvas = document.createElement('canvas');
        canvas.width = CANVAS_WIDTH;
        canvas.height = CANVAS_HEIGHT;
        document.body.appendChild(canvas);
        const ctx = canvas.getContext('2d');
        if (ctx) {
          const handler = await canvgPromise.then((canvg) =>
            canvg.from(ctx, svgString),
          );
          handler.start();
          await sleep(10);
          const imageBlob = await new Promise<Blob | null>((resolve) =>
            canvas.toBlob(resolve, BITMAP_MIME_TYPE),
          );
          if (imageBlob) {
            images.push({
              content: imageBlob,
              contentType: BITMAP_MIME_TYPE,
              width: CANVAS_WIDTH,
              height: CANVAS_HEIGHT,
              dpi: 90,
              anchor: { row: 1, column: 1 },
            });
            console.log('pushed image');
          } else {
            console.error('Unable to generate PNG blob from SVG -> Canvas');
          }
        } else {
          console.error("Can't get canvas context");
        }
        document.body.removeChild(canvas);
      }

      return {
        name,
        rows,
        images,
      };
    }),
  );

  return sheets;
};

const sleep = (delayMs: number) =>
  new Promise((resolve) => setTimeout(resolve, delayMs));
