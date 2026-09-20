import { resolveArtifactUrl } from '../api/client';
import type { ScanRecord } from '../types/contracts';

interface DownloadButtonsProps {
  scan: ScanRecord;
}

export default function DownloadButtons({ scan }: DownloadButtonsProps) {
  if (!scan.artifacts) return null;

  return (
    <div className="download-buttons" style={{ display: 'flex', gap: '16px', marginTop: '16px', flexWrap: 'wrap' }}>
      {scan.artifacts.report_pdf && (
        <a 
          href={resolveArtifactUrl(scan.artifacts.report_pdf) || '#'}
          className="btn-secondary"
          target="_blank" 
          rel="noreferrer"
        >
          REPORT PDF
          <svg className="btn-arrow" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ marginLeft: '4px' }}>
            <path d="M6 2L6 10M6 10L3 7M6 10L9 7" strokeLinecap="square" strokeLinejoin="miter"/>
          </svg>
        </a>
      )}
      {scan.artifacts.report_csv && (
        <a 
          href={resolveArtifactUrl(scan.artifacts.report_csv) || '#'}
          className="btn-secondary"
          target="_blank" 
          rel="noreferrer"
        >
          DATA CSV
          <svg className="btn-arrow" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ marginLeft: '4px' }}>
            <path d="M6 2L6 10M6 10L3 7M6 10L9 7" strokeLinecap="square" strokeLinejoin="miter"/>
          </svg>
        </a>
      )}
      {scan.artifacts.report_json && (
        <a 
          href={resolveArtifactUrl(scan.artifacts.report_json) || '#'}
          className="btn-secondary"
          target="_blank" 
          rel="noreferrer"
        >
          RECORD JSON
          <svg className="btn-arrow" width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="1.5" style={{ marginLeft: '4px' }}>
            <path d="M6 2L6 10M6 10L3 7M6 10L9 7" strokeLinecap="square" strokeLinejoin="miter"/>
          </svg>
        </a>
      )}
    </div>
  );
}
