import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import './ScanPage.css';

export default function ScanPage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [labelWidth, setLabelWidth] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0); // Optional visual only
  
  // Processing state
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [pollingStatus, setPollingStatus] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    if (e.target.files && e.target.files.length > 0) {
      const selectedFile = e.target.files[0];
      const validTypes = ['image/jpeg', 'image/png', 'application/pdf'];
      if (!validTypes.includes(selectedFile.type)) {
        setError('Unsupported file type. Please upload JPEG, PNG, or PDF.');
        setFile(null);
        return;
      }
      if (selectedFile.size > 20 * 1024 * 1024) {
        setError('File is too large. Maximum size is 20MB.');
        setFile(null);
        return;
      }
      setFile(selectedFile);
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsUploading(true);
    setError(null);

    try {
      const parsedWidth = labelWidth ? parseFloat(labelWidth) : undefined;
      
      // Step 1: Request upload URL
      setUploadProgress(10);
      const res = await apiClient.requestUpload({
        filename: file.name,
        content_type: file.type,
        label_width_mm: parsedWidth,
      });

      // Step 2: Upload to S3
      setUploadProgress(40);
      await apiClient.uploadFileToS3(res.upload_url, file);
      
      // Step 3: Transition to polling
      setUploadProgress(100);
      setActiveScanId(res.scan_id);
      setPollingStatus('PENDING');

    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'An error occurred during upload.');
    } finally {
      setIsUploading(false);
    }
  };

  useEffect(() => {
    if (!activeScanId) return;

    let timeoutId: number;

    const poll = async () => {
      try {
        const scan = await apiClient.getScan(activeScanId);
        setPollingStatus(scan.status);

        if (['DONE', 'NEEDS_REVIEW', 'FAILED'].includes(scan.status)) {
          // Terminal state reached, navigate to report
          navigate(`/report/${activeScanId}`);
        } else {
          // Continue polling
          timeoutId = window.setTimeout(poll, 2000);
        }
      } catch (err: unknown) {
        // If getting scan fails, we can retry or abort
        setError('Failed to poll scan status: ' + (err instanceof Error ? err.message : String(err)));
        timeoutId = window.setTimeout(poll, 5000); // Backoff
      }
    };

    poll();

    return () => {
      clearTimeout(timeoutId);
    };
  }, [activeScanId, navigate]);

  return (
    <div className="scan-page">
      <div className="scan-container">
        <h1>Scan a Package</h1>
        
        {activeScanId ? (
          <div className="processing-state">
            <h2>Processing your label...</h2>
            <p>Scan ID: {activeScanId}</p>
            <div className="status-indicator">
              <span className="spinner"></span>
              <span className="status-text">Status: {pollingStatus}</span>
            </div>
            <p className="hint">You will be redirected automatically when done.</p>
          </div>
        ) : (
          <div className="upload-state">
            <p className="subtitle">Upload a photo or PDF of a product label to verify compliance.</p>
            
            {error && <div className="error-banner">{error}</div>}
            
            <div className="upload-card">
              <div className="file-input-group">
                <label>Select File</label>
                <input 
                  type="file" 
                  accept=".jpg,.jpeg,.png,.pdf" 
                  onChange={handleFileChange} 
                  ref={fileInputRef}
                  disabled={isUploading}
                />
                <small>Max 20MB. JPEG, PNG, or PDF.</small>
              </div>

              {file && !file.type.includes('pdf') && (
                <div className="input-group">
                  <label htmlFor="labelWidth">Label Width (mm) <span className="optional">(Optional)</span></label>
                  <input 
                    id="labelWidth"
                    type="number" 
                    step="0.1" 
                    min="0"
                    placeholder="e.g. 90" 
                    value={labelWidth} 
                    onChange={e => setLabelWidth(e.target.value)}
                    disabled={isUploading}
                  />
                  <small>Improves numeral height measurement accuracy (Rule 8).</small>
                </div>
              )}

              <button 
                className="btn-primary" 
                onClick={handleUpload}
                disabled={!file || isUploading}
              >
                {isUploading ? `Uploading... ${uploadProgress}%` : 'Upload and Scan'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
