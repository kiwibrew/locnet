import { getSheets } from './sheets';

const MINIMUM_PRINT_TIME_MS = 4000;

export const exportCSV = async (selector: string) => {
  const printModeClassName = 'print-mode';
  document.body.classList.add(printModeClassName);
  const startTimeMs = Date.now();
  const exportElm = document.querySelector<HTMLDivElement>(selector);
  if (!exportElm) {
    alert(`Can't find element at ${JSON.stringify(selector)}`);
    return;
  }

  const sheets = await getSheets(exportElm);

  import('@vanillaes/csv').then(async (csv) => {
    const timeToGeneratePDFinMs = Date.now() - startTimeMs;
    // for UX reasons ensure a minimum speed rather than flashing the screen
    void (await sleep(
      Math.max(0, MINIMUM_PRINT_TIME_MS - timeToGeneratePDFinMs),
    ));

    const timestamp = new Date().toISOString().replace(/T/g, '_');

    const sheetData = sheets.reduce(
      (acc, sheet) => {
        acc.push([sheet.name]);
        sheet.rows.forEach((row) => {
          acc.push(row.map((cell) => cell.value ?? ''));
        });
        acc.push([]);
        return acc;
      },
      [] as (number | string)[][],
    );

    const csvText = csv.stringify(sheetData);
    const blob = new Blob([csvText], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `Community Network Builder Export - ${timestamp}.csv`;
    document.body.appendChild(a);
    a.click();
    await sleep(50); // wait for spreadsheet to load
    document.body.classList.remove(printModeClassName);
    setTimeout(() => document.body.removeChild(a), 100);
  });
};

const sleep = (delayMs: number) =>
  new Promise((resolve) => setTimeout(resolve, delayMs));
