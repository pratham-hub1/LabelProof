import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { ScanRecord, RuleResultStatus } from '../types/contracts';
import EvidenceViewer from '../components/EvidenceViewer';
import DownloadButtons from '../components/DownloadButtons';
import './ReportPage.css';

export default function ReportPage() {
  const { scanId } = useParams<{ scanId: string }>();
  const [scan, setScan] = useState<ScanRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // For EvidenceViewer interaction
  const [activeBoxId, setActiveBoxId] = useState<string | null>(null);

  useEffect(() => {
    if (!scanId) return;
    
    const fetchScan = async () => {
      try {
        setLoading(true);
        const data = await apiClient.getScan(scanId);
        setScan(data);
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to fetch scan report');
      } finally {
        setLoading(false);
      }
    };
    fetchScan();
  }, [scanId]);

  if (loading) {
    return (
      <div className="report-page state-container">
        <div className="spinner"></div>
      </div>
    );
  }

  if (error || !scan) {
    return (
      <div className="report-page">
        <div className="empty-state" style={{ margin: '0 auto', marginTop: '100px' }}>
          <div className="empty-state-ghost">04</div>
          <p className="empty-state-text">NO REPORT AVAILABLE</p>
          <p className="empty-state-subtext">{error || 'The requested scan ID does not exist or failed.'}</p>
        </div>
      </div>
    );
  }

  // Handle FAILED scan appropriately (strict requirement)
  if (scan.status === 'FAILED') {
    return (
      <div className="report-page failed">
        <div className="failed-banner">
          <h2>Scan Failed</h2>
          {scan.error ? (
            <>
              <p><strong>Code:</strong> {scan.error.code}</p>
              <p><strong>Message:</strong> {scan.error.message}</p>
            </>
          ) : (
            <p>The scan failed due to an unknown internal error.</p>
          )}
        </div>
      </div>
    );
  }

  // Handle PENDING/PROCESSING fallback (should theoretically be handled by ScanPage polling, but just in case)
  if (scan.status === 'PENDING' || scan.status === 'PROCESSING') {
    return (
      <div className="report-page loading">
        <div className="spinner"></div>
        <p>Scan is still processing. Status: {scan.status}</p>
      </div>
    );
  }

  // Prepare boxes for Evidence Viewer
  const viewerBoxes: Array<{ id: string; box: [number, number, number, number]; label: string; color: string }> = [];
  if (scan.results) {
    scan.results.forEach((r) => {
      if (r.box) {
        let color = '#4caf50'; // PASS
        if (r.status === 'FAIL') color = '#f44336';
        if (r.status === 'NEEDS_REVIEW') color = '#ff9800';
        if (r.status === 'NA') color = '#9e9e9e';

        // Only highlight if it's the active box, or if no active box is selected, show all
        if (!activeBoxId || activeBoxId === r.rule_id) {
          viewerBoxes.push({
            id: r.rule_id,
            box: r.box,
            label: r.rule_id,
            color: activeBoxId === r.rule_id ? '#2196f3' : color, // Blue if actively selected
          });
        }
      }
    });
  }

  const getStatusColor = (status: RuleResultStatus) => {
    switch(status) {
      case 'PASS': return 'status-pass';
      case 'FAIL': return 'status-fail';
      case 'NEEDS_REVIEW': return 'status-review';
      case 'NA': return 'status-na';
      default: return '';
    }
  };

  return (
    <div className="report-page">
      <header className="report-header page-header">
        <div className="header-info">
          <span className="page-header-id reveal-1">04 / RESULT</span>
          <h1 className="page-header-title reveal-2">Compliance Verdict</h1>
          <div className="page-header-desc reveal-3">
            <div className="metadata-row">
              <span className="label">TARGET</span>
              <span className="value">{scan.product?.brand_guess} {scan.product?.generic_name || 'Unknown Product'}</span>
            </div>
            <div className="metadata-row">
              <span className="label">SCAN ID</span>
              <span className="value">{scan.scan_id}</span>
            </div>
            <div className="metadata-row">
              <span className="label">TIMESTAMP</span>
              <span className="value">{new Date(scan.updated_at).toLocaleString()}</span>
            </div>
          </div>
          <div className="report-actions">
            <DownloadButtons scan={scan} />
          </div>
        </div>
        
        {scan.summary && (
          <div className="verdict-panel reveal-4">
            <div className={`verdict-status ${scan.summary.fail > 0 ? 'status-fail' : (scan.summary.needs_review > 0 ? 'status-review' : 'status-pass')}`}>
              {scan.summary.fail > 0 ? 'NON-COMPLIANT' : (scan.summary.needs_review > 0 ? 'NEEDS REVIEW' : 'COMPLIANT')}
            </div>
            <div className="summary-stats">
              <div className="stat-box">
                <span className="stat-label">VIOLATIONS</span>
                <span className={`stat-num ${scan.summary.fail > 0 ? 'fail-text' : ''}`}>{scan.summary.fail}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">REVIEWS</span>
                <span className={`stat-num ${scan.summary.needs_review > 0 ? 'review-text' : ''}`}>{scan.summary.needs_review}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">PASSED</span>
                <span className="stat-num pass-text">{scan.summary.pass}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">DECLARATIONS</span>
                <span className="stat-num">{scan.summary.found_declarations ?? 0}/7</span>
              </div>
            </div>
          </div>
        )}
      </header>

      {scan.exemption?.applied && (
        <div className="exemption-banner">
          <h3>Exemption Applied: {scan.exemption.citation}</h3>
          <p>{scan.exemption.reason}</p>
          <p className="note">This scan is exempt. Results are marked NA.</p>
        </div>
      )}

      <div className="report-content reveal-4">
        <div className="report-left-column">
          <div className="results-list">
            <h2>Rule Results</h2>
            {scan.results?.map((result) => (
            <div 
              key={result.rule_id} 
              className={`result-card ${getStatusColor(result.status)} ${activeBoxId === result.rule_id ? 'active' : ''}`}
              onMouseEnter={() => setActiveBoxId(result.rule_id)}
              onMouseLeave={() => setActiveBoxId(null)}
            >
              <div className="result-header">
                <span className="rule-id">{result.rule_id}</span>
                <span className={`status-badge ${getStatusColor(result.status)}`}>{result.status}</span>
              </div>
              <h3 className="rule-name">{result.name}</h3>
              <p className="citation">{result.citation}</p>
              
              {result.evidence && (
                <div className="evidence-text">
                  <strong>Evidence:</strong> {result.evidence}
                </div>
              )}
              
              {result.fix && (
                <div className="fix-text">
                  <strong>Fix:</strong> {result.fix}
                </div>
              )}
              
              {result.measurement && (
                <div className="measurement-info">
                  <strong>Measurement:</strong> {result.measurement.measured_mm}mm (Req: {result.measurement.required_mm}mm)
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="declarations-section">
          <h2>Extracted Declarations</h2>
          {scan.extraction?.fields ? (
            <div className="declarations-grid">
              {Object.entries(scan.extraction.fields).map(([key, field]) => {
                if (!field || typeof field !== 'object' || !('raw' in field)) return null;
                return (
                  <div className="declaration-cell" key={key}>
                    <span className="dec-label">{key.replace(/_/g, ' ').toUpperCase()}</span>
                    <span className="dec-value">{field.raw || 'Not detected'}</span>
                    <span className="dec-conf">Confidence: {(field.confidence * 100).toFixed(1)}%</span>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="no-evidence"><p>No declarations extracted.</p></div>
          )}
        </div>
        </div>

        <div className="evidence-section">
          <h2>Evidence Viewer</h2>
          {scan.artifacts?.display_image && scan.extraction?.image ? (
            <EvidenceViewer 
              imageUrl={scan.artifacts.display_image}
              originalWidth={scan.extraction.image.width}
              originalHeight={scan.extraction.image.height}
              boxes={viewerBoxes}
            />
          ) : (
            <div className="no-evidence">
              <p>No visual evidence available for this scan.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
