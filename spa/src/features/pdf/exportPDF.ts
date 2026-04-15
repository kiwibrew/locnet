const MINIMUM_PRINT_TIME_MS = 2000;

export const exportPdf = (selector: string) => {
  const printModeClassName = 'print-mode';
  document.body.classList.add(printModeClassName);
  const startTimeMs = Date.now();
  import(
    // @ts-expect-error this doesn't have typescript libs
    'dompdf.js'
  ).then((module) => {
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
    };
    const dompdf = module.default;

    const exportElm = document.querySelector<HTMLDivElement>(selector);
    if (!exportElm) {
      alert(`Can't find element at ${JSON.stringify(selector)}`);
      return;
    }

    dompdf(exportElm, options)
      .then(async (blob: Blob) => {
        const timeToGeneratePDFinMs = Date.now() - startTimeMs;
        void (await sleep(
          Math.max(0, MINIMUM_PRINT_TIME_MS - timeToGeneratePDFinMs),
        ));
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        const timestamp = (new Date()).toISOString().replace(/T/g, '_')
        a.download = `Community Network Builder Export - ${timestamp}.pdf`;
        document.body.appendChild(a);
        a.click();
        await sleep(100); // wait for PDF reader to open
        document.body.classList.remove(printModeClassName);
        setTimeout(() => document.body.removeChild(a), 100);
      })
      .catch((err: unknown) => {
        console.error(err);
      });
  });
};

const sleep = (delayMs: number) =>
  new Promise((resolve) => setTimeout(resolve, delayMs));
