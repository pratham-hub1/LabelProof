import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../api/client';
import type { ScanRecord } from '../types/contracts';
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
  const [currentScan, setCurrentScan] = useState<ScanRecord | null>(null);
  
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

    let parsedWidth: number | undefined;
    if (!file.type.includes('pdf')) {
      parsedWidth = parseFloat(labelWidth);
      if (isNaN(parsedWidth) || parsedWidth <= 0) {
        setError('Physical label width is required and must be greater than 0 for image uploads.');
        return;
      }
    }

    setIsUploading(true);
    setError(null);

    try {
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
    let isMounted = true;

    const poll = async () => {
      try {
        const scan = await apiClient.getScan(activeScanId);
        if (!isMounted) return;
        setPollingStatus(scan.status);
        setCurrentScan(scan);

        if (['DONE', 'NEEDS_REVIEW', 'FAILED'].includes(scan.status)) {
          // Terminal state reached, navigate to report
          navigate(`/report/${activeScanId}`);
        } else {
          // Continue polling
          timeoutId = window.setTimeout(poll, 3000);
        }
      } catch (err: unknown) {
        if (!isMounted) return;
        // If getting scan fails, we can retry or abort
        setError('Failed to poll scan status: ' + (err instanceof Error ? err.message : String(err)));
        timeoutId = window.setTimeout(poll, 5000); // Backoff
      }
    };

    poll();

    return () => {
      isMounted = false;
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
            
            {error && <div className="error-banner">{error}</div>}
            {currentScan?.error && (
              <div className="error-banner">
                <strong>{currentScan.error.code}</strong>: {currentScan.error.message}
              </div>
            )}

            <div className="processing-steps" style={{ marginTop: '32px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className={`processing-step ${currentScan ? 'completed' : 'active'}`}>
                <span className="step-icon">{currentScan ? '✓' : '⟳'}</span>
                <span className="step-text">Image received</span>
              </div>
              
              <div className={`processing-step ${currentScan?.extraction ? 'completed' : (currentScan ? 'active' : 'waiting')}`}>
                <span className="step-icon">{currentScan?.extraction ? '✓' : (currentScan ? '⟳' : '○')}</span>
                <span className="step-text">AI is reading the label</span>
                {currentScan?.extraction?.fields && (
                  <div className="extraction-preview" style={{ marginLeft: '24px', fontSize: '12px', opacity: 0.8, marginTop: '4px' }}>
                    {Object.entries(currentScan.extraction.fields).map(([key, field]) => {
                      if (!field || !field.raw) return null;
                      return (
                        <div key={key} style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span>{key}: {field.raw}</span>
                          <span>{field.confidence ? `${(field.confidence * 100).toFixed(0)}%` : ''}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              <div className={`processing-step ${currentScan?.results ? 'completed' : (currentScan?.extraction ? 'active' : 'waiting')}`}>
                <span className="step-icon">{currentScan?.results ? '✓' : (currentScan?.extraction ? '⟳' : '○')}</span>
                <span className="step-text">Verifying 11 legal rules</span>
              </div>

              <div className={`processing-step ${['DONE', 'NEEDS_REVIEW', 'FAILED'].includes(currentScan?.status || '') ? 'completed' : (currentScan?.results ? 'active' : 'waiting')}`}>
                <span className="step-icon">{['DONE', 'NEEDS_REVIEW', 'FAILED'].includes(currentScan?.status || '') ? '✓' : (currentScan?.results ? '⟳' : '○')}</span>
                <span className="step-text">Generating report</span>
              </div>
            </div>

            <div className="processing-metadata" style={{ marginTop: '32px' }}>
              <span className="label">TARGET ID</span>
              <span className="value">{activeScanId}</span>
              <span className="label" style={{ marginLeft: '16px' }}>STATUS</span>
              <span className="value">{pollingStatus}</span>
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
            
            <div className="upload-layout reveal-4">
              <div className="upload-left">
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
              </div>

              <div className="upload-right">
                {file && !file.type.includes('pdf') && (
                  <div className="input-group">
                    <label htmlFor="labelWidth" className="technical-label">TARGET / LABEL WIDTH CALIBRATION</label>
                    <input 
                      id="labelWidth"
                      type="number" 
                      step="0.1" 
                      min="0"
                      placeholder="e.g. 90 (mm)" 
                      value={labelWidth} 
                      onChange={e => setLabelWidth(e.target.value)}
                      disabled={isUploading}
                    />
                    <small>Approximate physical width of the label in millimeters. Required for image uploads.</small>
                  </div>
                )}

                <div className="scan-info-note">
                  11-point LMPC (Legal Metrology) compliance check
                </div>

                <button 
                  className="btn-primary scan-action-btn" 
                  onClick={handleUpload}
                  disabled={!file || isUploading}
                >
                  {isUploading ? `PROCESSING [${uploadProgress}%]` : 'INITIATE INSPECTION'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
