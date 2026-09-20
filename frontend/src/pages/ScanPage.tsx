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
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  
  // Processing state
  const [activeScanId, setActiveScanId] = useState<string | null>(null);
  const [pollingStatus, setPollingStatus] = useState<string | null>(null);
  
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFile(e.dataTransfer.files[0]);
    }
  };

  const processFile = (selectedFile: File) => {
    setError(null);
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
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      processFile(e.target.files[0]);
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
        
        {activeScanId ? (
          <div className="processing-state">
            <span className="processing-eyebrow">INSPECTION IN PROGRESS</span>
            <h2>Machine Vision Analyzing...</h2>
            <div className="status-indicator">
              <span className="spinner"></span>
              <span className="status-text">{pollingStatus}</span>
            </div>
            <div className="processing-metadata">
              <span className="label">TARGET ID</span>
              <span className="value">{activeScanId}</span>
            </div>
          </div>
        ) : (
          <div className="upload-state">
            <div className="page-header">
              <span className="page-header-id reveal-1">01 / INTAKE</span>
              <h1 className="page-header-title reveal-2">Inspect a packaged commodity</h1>
              <p className="page-header-desc reveal-3">Upload a package label for automated compliance analysis.</p>
            </div>
            
            {error && <div className="error-banner reveal-4">{error}</div>}
            
            <div className="upload-card reveal-4">
              <div className="file-input-group">
                <label className="technical-label">INPUT / EVIDENCE UPLOAD</label>
                <div 
                  className="drop-zone-wrapper"
                  onDragEnter={handleDragEnter}
                  onDragOver={handleDragEnter}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                >
                  <input 
                    type="file" 
                    accept=".jpg,.jpeg,.png,.pdf" 
                    onChange={handleFileChange} 
                    ref={fileInputRef}
                    disabled={isUploading}
                    className={file ? 'has-file' : ''}
                  />
                  <div className={`drop-zone-content ${file ? 'active' : ''} ${isDragging ? 'armed' : ''}`}>
                    {/* Corner markers */}
                    <div className="corner top-left"></div>
                    <div className="corner top-right"></div>
                    <div className="corner bottom-left"></div>
                    <div className="corner bottom-right"></div>
                    
                    {!file ? (
                      <>
                        <span className="primary-inst">Select or drop file here</span>
                        <span className="secondary-inst">JPEG, PNG, or PDF up to 20MB</span>
                      </>
                    ) : (
                      <>
                        <span className="technical-label success-label">READY TO INSPECT</span>
                        <span className="file-name">{file.name}</span>
                        <span className="file-size">{(file.size / 1024 / 1024).toFixed(2)} MB</span>
                      </>
                    )}
                  </div>
                </div>
              </div>

              {file && !file.type.includes('pdf') && (
                <div className="input-group">
                  <label htmlFor="labelWidth" className="technical-label">TARGET / LABEL WIDTH CALIBRATION <span className="optional">(OPTIONAL)</span></label>
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
                  <small>Enter physical width in millimeters to calibrate numeral height checks.</small>
                </div>
              )}

              <button 
                className="btn-primary scan-action-btn" 
                onClick={handleUpload}
                disabled={!file || isUploading}
              >
                {isUploading ? `PROCESSING [${uploadProgress}%]` : 'INITIATE INSPECTION'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
