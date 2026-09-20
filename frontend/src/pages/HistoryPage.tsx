import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { ScanRecord } from '../types/contracts';
import './HistoryPage.css';

export default function HistoryPage() {
  const navigate = useNavigate();
  const [scans, setScans] = useState<ScanRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastKey, setLastKey] = useState<string | null>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);

  const fetchScans = async (cursor?: string) => {
    try {
      if (!cursor) setLoading(true);
      else setIsLoadingMore(true);
      
      const res = await apiClient.listScans({ limit: 20, last_key: cursor });
      
      if (cursor) {
        setScans((prev) => [...prev, ...res.items]);
      } else {
        setScans(res.items);
      }
      setLastKey(res.last_key);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
      setIsLoadingMore(false);
    }
  };

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchScans();
  }, []);

  if (loading) {
    return (
      <div className="history-page state-container">
        <div className="spinner"></div>
        <p>Loading history...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="history-page state-container">
        <h2>Error Loading History</h2>
        <p className="error-text">{error}</p>
        <button className="btn-primary" style={{ marginTop: '16px' }} onClick={() => fetchScans()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="history-container">
        <div className="page-header">
          <span className="page-header-id reveal-1">
            <span className="numeral">02</span>
            <span className="identifier">ARCHIVE</span>
          </span>
          <h1 className="page-header-title reveal-2">Inspection Archive</h1>
          <p className="page-header-desc reveal-3">Review and access previously recorded compliance reports.</p>
        </div>
        
        {scans.length === 0 ? (
          <div className="empty-state reveal-4">
            <div className="empty-state-ghost">02</div>
            <p className="empty-state-text">NO INSPECTIONS RECORDED</p>
            <p className="empty-state-subtext">Upload a label in the intake console to create the first record.</p>
            <button className="btn-primary" onClick={() => navigate('/scan')}>INITIATE INSPECTION</button>
          </div>
        ) : (
          <>
            <div className="scans-list reveal-4">
              {scans.map((scan) => (
                <div 
                  key={scan.scan_id} 
                  className={`scan-card status-${scan.status.toLowerCase()}`}
                  onClick={() => navigate(`/report/${scan.scan_id}`)}
                >
                  <div className="col-product">
                    <span className="product-name">
                      {scan.product?.brand_guess || scan.product?.generic_name 
                        ? `${scan.product.brand_guess || ''} ${scan.product.generic_name || ''}`.trim() 
                        : scan.input?.filename || 'Unknown Product'}
                    </span>
                    <span className="scan-id">ID: {scan.scan_id}</span>
                  </div>
                  
                  <div className="col-date">
                    <span className="scan-date">{new Date(scan.created_at).toLocaleDateString()} {new Date(scan.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}</span>
                  </div>
                  
                  <div className="col-verdict">
                    <span className={`scan-status status-badge ${scan.status.toLowerCase()}`}>
                      {scan.status === 'DONE' ? 'COMPLIANT' : 
                       scan.status === 'FAILED' ? (scan.results ? 'NON-COMPLIANT' : 'PROCESSING FAILED') : 
                       scan.status === 'NEEDS_REVIEW' ? 'REVIEW NEEDED' : scan.status}
                    </span>
                    {scan.status === 'FAILED' && scan.error && !scan.results && (
                      <div className="scan-card-error">
                        {scan.error.code}
                      </div>
                    )}
                  </div>
                  
                  <div className="col-summary">
                    {scan.summary ? (
                      <div className="scan-card-summary">
                        <span className="fail">{scan.summary.fail} FAIL</span>
                        <span className="pass">{scan.summary.pass} PASS</span>
                        <span className="review">{scan.summary.needs_review} REVIEW</span>
                      </div>
                    ) : (
                      <span className="scan-card-summary empty">-</span>
                    )}
                  </div>

                  <div className="col-action">
                    <span className="action-text">View Report →</span>
                  </div>
                </div>
              ))}
            </div>
            
            {lastKey && (
              <div className="load-more-container">
                <button 
                  className="btn-secondary" 
                  onClick={() => fetchScans(lastKey)}
                  disabled={isLoadingMore}
                >
                  {isLoadingMore ? 'Loading...' : 'Load More'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
