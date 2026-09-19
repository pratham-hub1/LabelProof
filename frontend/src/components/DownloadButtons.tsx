import { apiClient } from '../api/client';
import type { ScanRecord } from '../types/contracts';

interface DownloadButtonsProps {
  scan: ScanRecord;
}

export default function DownloadButtons({ scan }: DownloadButtonsProps) {
  if (!scan.artifacts) return null;

  return (
    <div className="download-buttons" style={{ display: 'flex', gap: '8px', marginTop: '16px' }}>
      {scan.artifacts.report_pdf && (
        <a 
          href={apiClient.getReportDownloadUrl(scan.scan_id, 'pdf')}
          className="btn-download pdf"
          target="_blank" 
          rel="noreferrer"
        >
          Download PDF
        </a>
      )}
      {scan.artifacts.report_csv && (
        <a 
          href={apiClient.getReportDownloadUrl(scan.scan_id, 'csv')}
          className="btn-download csv"
          target="_blank" 
          rel="noreferrer"
        >
          Download CSV
        </a>
      )}
      {scan.artifacts.report_json && (
        <a 
          href={apiClient.getReportDownloadUrl(scan.scan_id, 'json')}
          className="btn-download json"
          target="_blank" 
          rel="noreferrer"
        >
          Download JSON
        </a>
      )}
    </div>
  );
}
