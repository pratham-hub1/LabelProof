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
        <button className="btn-retry" onClick={() => fetchScans()}>Retry</button>
      </div>
    );
  }

  return (
    <div className="history-page">
      <div className="history-container">
        <h1>Scan History</h1>
        
        {scans.length === 0 ? (
          <div className="empty-state">
            <p>No scans found.</p>
            <button className="btn-primary" onClick={() => navigate('/scan')}>Scan a Package</button>
          </div>
        ) : (
          <>
            <div className="scans-list">
              {scans.map((scan) => (
                <div 
                  key={scan.scan_id} 
                  className={`scan-card status-${scan.status.toLowerCase()}`}
                  onClick={() => navigate(`/report/${scan.scan_id}`)}
                >
                  <div className="scan-card-header">
                    <span className="scan-id">{scan.scan_id}</span>
                    <span className="scan-status">{scan.status}</span>
                  </div>
                  <div className="scan-card-body">
                    <p className="product-name">
                      {scan.product?.brand_guess || 'Unknown Brand'} - {scan.product?.generic_name || 'Unknown Product'}
                    </p>
                    <p className="scan-date">{new Date(scan.created_at).toLocaleString()}</p>
                  </div>
                  {scan.status === 'FAILED' && scan.error && (
                    <div className="scan-card-error">
                      Error: {scan.error.code}
                    </div>
                  )}
                  {scan.summary && (
                    <div className="scan-card-summary">
                      <span className="fail">{scan.summary.fail} Violations</span>
                      <span className="pass">{scan.summary.pass} Passed</span>
                    </div>
                  )}
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
