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

  import('write-excel-file').then(async (module) => {
    const writeXlsxFile = module.default;

    const timeToGeneratePDFinMs = Date.now() - startTimeMs;
    void (await sleep(
      Math.max(0, MINIMUM_PRINT_TIME_MS - timeToGeneratePDFinMs),
    ));

    const timestamp = new Date().toISOString().replace(/T/g, '_');

    const xlsxSheets = sheets.map((sheet) =>
      sheet.rows.map((row) => {
        return row.map((cell) => {
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
        });
      }),
    );

    console.log({ sheets, xlsxSheets })

    await writeXlsxFile(xlsxSheets, {
      fileName: `Community Network Builder Export - ${timestamp}.xlsx`,
      sheets: sheets.map((sheet) =>
        sheet.name.trim().substring(
          0,
          // excel format has max sheet name length of 31 chars
          31,
        ),
      ),
      images: sheets.map((sheet) => sheet.images),
    });

    await sleep(50); // wait for spreadsheet to load
    document.body.classList.remove(printModeClassName);
  });
};

const sleep = (delayMs: number) =>
  new Promise((resolve) => setTimeout(resolve, delayMs));
