import { z } from 'zod';
import { FormNodeSchema } from '../base';
import { type NodeProps } from '../node';
import { useCallback } from 'react';
import { Text } from '../Intl';
import styles from './ExportFiles.module.css';
import { TiDocument, TiDocumentText } from 'react-icons/ti';

export const ExportFilesSchema = FormNodeSchema.extend({
  type: z.literal('ExportFiles'),
  selector: z.string(),
  labelPDFIntlId: z.string().optional(),
  labelPDFText: z.string().optional(),
  labelExcelIntlId: z.string().optional(),
  labelExcelText: z.string().optional(),
  labelCSVIntlId: z.string().optional(),
  labelCSVText: z.string().optional(),
});

export type ExportFiles = z.infer<typeof ExportFilesSchema>;

type Props = NodeProps<ExportFiles>;

export const RenderExportFiles = ({ node }: Props) => {
  const handleExportPdf = useCallback(() => {
    import('../../pdf/exportPDF').then((module) =>
      module.exportPdf(node.selector),
    );
  }, [node.selector]);

  const handleExportExcel = useCallback(() => {
    import('../../excel/exportExcel').then((module) =>
      module.exportExcel(node.selector),
    );
  }, [node.selector]);

  const handleExportCSV = useCallback(() => {
    import('../../excel/exportCSV').then((module) =>
      module.exportCSV(node.selector),
    );
  }, [node.selector]);

  return (
    <div className={styles.container}>
      <h2 className={styles.labelText}>
        <Text intlId={node.labelIntlId} text={node.labelText} />
      </h2>
      <div className={styles.buttonTray}>
        <button
          type="button"
          className={styles.button}
          onClick={handleExportCSV}
        >
          <TiDocumentText size="1.4rem" />
          <Text intlId={node.labelCSVIntlId} text={node.labelCSVText} />
        </button>
        <button
          type="button"
          className={styles.button}
          onClick={handleExportExcel}
        >
          <TiDocumentText size="1.4rem" />
          <Text intlId={node.labelExcelIntlId} text={node.labelExcelText} />
        </button>
        <button
          type="button"
          className={styles.button}
          onClick={handleExportPdf}
        >
          <TiDocument size="1.4rem" />
          <Text intlId={node.labelPDFIntlId} text={node.labelPDFText} />
        </button>
      </div>
    </div>
  );
};
