import { getSheets } from './sheets';

const MINIMUM_PRINT_TIME_MS = 4000;

export const exportExcel = async (selector: string) => {
  const printModeClassName = 'print-mode';
  document.body.classList.add(printModeClassName);
  const startTimeMs = Date.now();
  const exportElm = document.querySelector<HTMLDivElement>(selector);
  if (!exportElm) {
    alert(`Can't find element at ${JSON.stringify(selector)}`);
    return;
  }

  const sheets = await getSheets(exportElm);

  import('write-excel-file/browser').then(async (module) => {
    const writeXlsxFile = module.default;

    const timeToGeneratePDFinMs = Date.now() - startTimeMs;
    void (await sleep(
      Math.max(0, MINIMUM_PRINT_TIME_MS - timeToGeneratePDFinMs),
    ));

    const timestamp = new Date().toISOString().replace(/T/g, '_');

    const xlsxSheets = sheets.map((sheet) => ({
      data: sheet.rows.map((row) =>
        row.map((cell) => {
          switch (cell.type) {
            case 'string':
              return {
                type: String,
                value: cell.value,
                fontWeight: cell.fontWeight,
              };
            case 'number':
              return {
                type: Number,
                value: cell.value,
                fontWeight: cell.fontWeight,
              };
            case 'date':
              return {
                type: Date,
                value: cell.value,
                fontWeight: cell.fontWeight,
              };
          }
        }),
      ),
      // Excel limits sheet names to 31 characters.
      sheet: sheet.name.trim().substring(0, 31),
      images: sheet.images,
    }));

    await writeXlsxFile(xlsxSheets).toFile(
      `Community Network Builder Export - ${timestamp}.xlsx`,
    );

    await sleep(50); // wait for spreadsheet to load
    document.body.classList.remove(printModeClassName);
  });
};

const sleep = (delayMs: number) =>
  new Promise((resolve) => setTimeout(resolve, delayMs));
