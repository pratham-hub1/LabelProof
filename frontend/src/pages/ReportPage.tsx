import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { apiClient, resolveArtifactUrl } from '../api/client';
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

  // Handle true API/transport failures that have no results
  if (scan.status === 'FAILED' && scan.error && !scan.results) {
    return (
      <div className="report-page failed">
        <div className="failed-banner">
          <h2>Scan Failed</h2>
          <p><strong>Code:</strong> {scan.error.code}</p>
          <p><strong>Message:</strong> {scan.error.message}</p>
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
          <span className="page-header-id reveal-1">
            <span className="numeral">04</span>
            <span className="identifier">RESULT</span>
          </span>
          <h1 className="page-header-title reveal-2">Inspection Report</h1>
          <div className="page-header-desc reveal-3">
            <div className="metadata-row">
              <span className="label">TARGET</span>
              <span className="value">{scan.product?.brand_guess} {scan.product?.generic_name || 'Unknown Product'}</span>
            </div>
            <div className="metadata-row">
              <span className="label">TIMESTAMP</span>
              <span className="value">{new Date(scan.updated_at).toLocaleString()}</span>
            </div>
            <div className="metadata-row">
              <span className="label">SCAN ID</span>
              <span className="value" style={{opacity: 0.6}}>{scan.scan_id}</span>
            </div>
          </div>
          <div className="report-actions">
            <DownloadButtons scan={scan} />
          </div>
        </div>
        
        {scan.summary && (
          <div className="verdict-panel reveal-4">
            <div className={`verdict-status ${scan.status === 'DONE' ? 'status-pass' : scan.status === 'FAILED' ? 'status-fail' : scan.status === 'NEEDS_REVIEW' ? 'status-review' : ''}`}>
              {scan.status === 'DONE' ? 'COMPLIANT' : 
               scan.status === 'FAILED' ? 'NON-COMPLIANT' : 
               scan.status === 'NEEDS_REVIEW' ? 'HUMAN REVIEW NEEDED' : scan.status}
            </div>
            <div className="verdict-explanation">
              {scan.status === 'DONE' ? 'All evaluated requirements passed.' :
               scan.status === 'FAILED' ? `${scan.summary.fail} requirement${scan.summary.fail === 1 ? '' : 's'} failed.` :
               scan.status === 'NEEDS_REVIEW' ? 'Some requirements require manual verification.' : ''}
            </div>
            <div className="summary-stats">
              <div className="stat-box">
                <span className="stat-label">PASS</span>
                <span className="stat-num pass-text">{scan.summary.pass}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">FAIL</span>
                <span className={`stat-num ${scan.summary.fail > 0 ? 'fail-text' : ''}`}>{scan.summary.fail}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">REVIEW</span>
                <span className={`stat-num ${scan.summary.needs_review > 0 ? 'review-text' : ''}`}>{scan.summary.needs_review}</span>
              </div>
              <div className="stat-box">
                <span className="stat-label">NOT APPLICABLE</span>
                <span className="stat-num">{scan.summary.na || 0}</span>
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
              onClick={(e) => {
                const el = e.currentTarget;
                el.classList.toggle('expanded');
              }}
              style={{ cursor: 'pointer' }}
            >
              <div className="result-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px' }}>
                    <span className="rule-id">{result.rule_id}</span>
                    <h3 className="rule-name" style={{ margin: 0 }}>{result.name}</h3>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <span className={`status-badge ${getStatusColor(result.status)}`}>
                      {result.status === 'PASS' ? 'Requirement satisfied' :
                       result.status === 'FAIL' ? 'Requirement not satisfied' :
                       result.status === 'NEEDS_REVIEW' ? 'Requires human review' :
                       result.status === 'NA' ? 'Not applicable' : result.status}
                    </span>
                  </div>
                </div>
                
                <div className="chevron-icon" style={{ opacity: 0.5, transition: 'transform 0.3s ease' }}>
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                    <polyline points="6 9 12 15 18 9"></polyline>
                  </svg>
                </div>
              </div>
              
              <div className="expandable-content" style={{ overflow: 'hidden', height: 0, opacity: 0, transition: 'all 0.3s ease-out' }}>
                <div style={{ marginTop: '16px', paddingTop: '24px', borderTop: '1px solid rgba(255,255,255,0.1)', display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  
                  {result.evidence && (
                    <div className="evidence-section">
                      <span className="technical-label" style={{ display: 'block', marginBottom: '8px', color: 'var(--color-text-secondary)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>CHECK DETAIL</span>
                      <div className="evidence-text" style={{ fontSize: '1rem', color: 'var(--color-text-primary)' }}>
                        {result.evidence}
                      </div>
                      {result.measurement && (
                        <div className="measurement-info" style={{ marginTop: '8px', fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
                          Measured: {result.measurement.measured_mm}mm (Required: {result.measurement.required_mm}mm)
                        </div>
                      )}
                    </div>
                  )}
                  
                  {result.fix && (
                    <div className="fix-section">
                      <span className="technical-label" style={{ display: 'block', marginBottom: '8px', color: 'var(--color-status-warning)', fontSize: '0.75rem', fontFamily: 'var(--font-mono)' }}>RECOMMENDED ACTION</span>
                      <div className="fix-text" style={{ fontSize: '1rem', color: 'var(--color-text-primary)' }}>
                        {result.fix}
                      </div>
                    </div>
                  )}

                  {!result.evidence && !result.fix && (
                     <div style={{ color: 'var(--color-text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
                       No additional detail was returned for this rule.
                     </div>
                  )}

                  <div className="citation-section" style={{ paddingTop: '16px', borderTop: '1px dashed rgba(255,255,255,0.05)' }}>
                    <span className="technical-label" style={{ display: 'block', marginBottom: '4px', color: 'var(--color-text-muted)', fontSize: '0.7rem', fontFamily: 'var(--font-mono)' }}>LEGAL REFERENCE</span>
                    <p className="citation" style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>{result.citation}</p>
                  </div>

                </div>
              </div>
              <div className="expand-hint" style={{ marginTop: '12px', fontSize: '10px', opacity: 0.5, textTransform: 'uppercase', transition: 'opacity 0.2s' }}>
                Click to expand details
              </div>
            </div>
          ))}
        </div>

        <div className="declarations-section">
          <h2>EXTRACTED LABEL DATA</h2>
          {scan.extraction?.fields ? (
            <div className="declarations-grid">
              {Object.entries(scan.extraction.fields).map(([key, field]) => {
                if (!field || typeof field !== 'object' || !('raw' in field)) return null;
                const confClass = field.confidence && field.confidence < 0.8 ? 'low-conf' : '';
                return (
                  <div className={`declaration-cell ${confClass}`} key={key}>
                    <span className="dec-label">{key.replace(/_/g, ' ').toUpperCase()}</span>
                    <span className="dec-value">{field.raw || 'Not found on label'}</span>
                    {field.raw && (
                      <span className="dec-conf">
                        {field.confidence !== null && field.confidence !== undefined ? `${(field.confidence * 100).toFixed(0)}% CONFIDENCE` : 'N/A'}
                      </span>
                    )}
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
          <h2>EVIDENCE IMAGE</h2>
          <p style={{marginBottom: '16px', color: 'var(--color-text-secondary)', fontSize: '0.9rem'}}>Annotated package image used during the compliance inspection.</p>
          {scan.artifacts?.display_image && scan.extraction?.image ? (
            <EvidenceViewer 
              imageUrl={resolveArtifactUrl(scan.artifacts.display_image) || ''}
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

      <footer className="report-footer">
        <div className="footer-content">
          <span>{scan.scan_id}</span>
          <span>{new Date(scan.updated_at).toLocaleString()}</span>
          <span>LMPC (PC) Rules, 2011</span>
        </div>
      </footer>
    </div>
  );
}
