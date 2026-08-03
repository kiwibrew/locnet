import type { ExportOptions } from 'dompdf.js';

const MINIMUM_PRINT_TIME_MS = 2000;
const MAP_SNAPSHOT_TIMEOUT_MS = 4000;

const waitForMapSnapshots = (
  exportElement: HTMLElement,
  timeoutMs = MAP_SNAPSHOT_TIMEOUT_MS,
) =>
  new Promise<void>((resolve) => {
    const hasPendingMaps = () =>
      Boolean(
        exportElement.querySelector('[data-pdf-map-status="loading"]'),
      );

    if (!hasPendingMaps()) {
      resolve();
      return;
    }

    const observer = new MutationObserver(() => {
      if (!hasPendingMaps()) {
        clearTimeout(timeoutId);
        observer.disconnect();
        resolve();
      }
    });
    observer.observe(exportElement, {
      attributes: true,
      attributeFilter: ['data-pdf-map-status'],
      subtree: true,
    });
    const timeoutId = setTimeout(() => {
      observer.disconnect();
      resolve();
    }, timeoutMs);
  });

export const exportPdf = async (selector: string) => {
  const printModeClassName = 'print-mode';
  const startTimeMs = Date.now();
  const exportElm = document.querySelector<HTMLDivElement>(selector);
  if (!exportElm) {
    alert(`Can't find element at ${JSON.stringify(selector)}`);
    return;
  }

  await waitForMapSnapshots(exportElm);
  document.body.classList.add(printModeClassName);

  try {
    const module = await import('dompdf.js');
    const options = {
      pagination: true,
      format: 'a4',
      pageConfig: {
        header: {
          height: 25,
        },
        footer: {
          content: 'Page ${currentPage} of ${totalPages}',
          height: 50,
          contentColor: '#333333',
          contentFontSize: 12,
          contentPosition: 'center',
          padding: [0, 0, 0, 0],
        },
      },
    } satisfies ExportOptions;
    const blob = await module.default(exportElm, options);
    const timeToGeneratePDFinMs = Date.now() - startTimeMs;
    await sleep(Math.max(0, MINIMUM_PRINT_TIME_MS - timeToGeneratePDFinMs));
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const timestamp = new Date().toISOString().replace(/T/g, '_');
    a.download = `Community Network Builder Export - ${timestamp}.pdf`;
    document.body.appendChild(a);
    a.click();
    await sleep(100); // wait for PDF reader to open
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (error) {
    console.error(error);
  } finally {
    document.body.classList.remove(printModeClassName);
  }
};

const sleep = (delayMs: number) =>
  new Promise((resolve) => setTimeout(resolve, delayMs));
