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
              <span className="page-header-id reveal-1">
                <span className="numeral">01</span>
                <span className="identifier">INTAKE</span>
              </span>
              <h1 className="page-header-title reveal-2">Compliance Console</h1>
              <p className="page-header-desc reveal-3">Inspect a packaged commodity. Upload imagery to verify regulatory adherence.</p>
            </div>
            
            {error && <div className="error-banner reveal-4">{error}</div>}

            <div className="upload-guidance reveal-4">
              <h2 className="guidance-title">Before you upload</h2>
              <p className="guidance-subtitle">Choose the instructions that match the type of label you are uploading.</p>
              
              <div className="guidance-cards">
                <div className="guidance-card">
                  <h3>
                    <span className="icon">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
                    </span>
                    1. If you have a photo of the label
                  </h3>
                  <p className="card-desc">For the most reliable analysis, make sure the physical label is captured clearly and straight-on.</p>
                  
                  <h4>Before you scan:</h4>
                  <ul className="guidance-list">
                    <li>
                      <span className="check">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </span>
                      <div>
                        <strong>Keep the label flat and facing the camera directly.</strong>
                        <span>For example: a chips packet, carton, or box front face.</span>
                      </div>
                    </li>
                    <li>
                      <span className="check">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </span>
                      <div>
                        <strong>Make sure the text is readable and not blurry.</strong>
                      </div>
                    </li>
                    <li>
                      <span className="check">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </span>
                      <div>
                        <strong>Use good, even lighting.</strong>
                        <span>Avoid harsh shadows or reflections across the text.</span>
                      </div>
                    </li>
                    <li>
                      <span className="check">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </span>
                      <div>
                        <strong>Measure the physical label width in millimetres with a ruler.</strong>
                        <span>This is required for geometry checks such as numeral height and clear space.</span>
                      </div>
                    </li>
                  </ul>

                  <div className="guidance-callout">
                    <div className="callout-header">
                      <span className="icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.3 15.3l-10-10a2 2 0 0 0-2.8 0l-5.7 5.7a2 2 0 0 0 0 2.8l10 10a2 2 0 0 0 2.8 0l5.7-5.7a2 2 0 0 0 0-2.8z"></path><line x1="14" y1="5.5" x2="16.5" y2="8"></line><line x1="10" y1="9.5" x2="12.5" y2="12"></line><line x1="6" y1="13.5" x2="8.5" y2="16"></line></svg>
                      </span>
                      <strong>Why do I need the label width?</strong>
                    </div>
                    <p>Label width lets LabelProof evaluate physical-size requirements that cannot be measured reliably from a photo alone. Without the width, geometry rules <span className="mono">R8</span> and <span className="mono">R9</span> will return <span className="mono">NEEDS_REVIEW</span> instead of a final verdict.</p>
                  </div>
                </div>

                <div className="guidance-card">
                  <h3>
                    <span className="icon">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    </span>
                    2. If you have a PDF of the label artwork
                  </h3>
                  <p className="card-desc">For artwork files, LabelProof can use the document's built-in dimensions.</p>

                  <h4>Before you upload:</h4>
                  <ul className="guidance-list">
                    <li>
                      <span className="check">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </span>
                      <div>
                        <strong>Upload the label artwork file.</strong>
                        <span>Vector or high-resolution artwork is recommended.</span>
                      </div>
                    </li>
                    <li>
                      <span className="check">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </span>
                      <div>
                        <strong>Only the first page is processed.</strong>
                        <span>If your artwork contains multiple pages, make sure the label is on page 1.</span>
                      </div>
                    </li>
                    <li>
                      <span className="check">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
                      </span>
                      <div>
                        <strong>You do not need to enter a label width.</strong>
                        <span>Dimensions are read directly from the PDF.</span>
                      </div>
                    </li>
                  </ul>

                  <div className="guidance-callout">
                    <div className="callout-header">
                      <span className="icon">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                      </span>
                      <strong>Why don't PDFs need a width?</strong>
                    </div>
                    <p>LabelProof reads the physical dimensions directly from the PDF artwork, so geometry checks such as <span className="mono">R8</span> can run using exact document measurements.</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="upload-layout reveal-4">
              <div className="upload-left">
                <div className="file-input-group">
                  <label className="technical-label">1. Upload Package Image</label>
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
                    <label htmlFor="labelWidth" className="technical-label">2. Enter Physical Label Width</label>
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
                    <small>Required for physical geometry checks such as numeral height and clear space.</small>
                  </div>
                )}

                <div className="scan-info-note">
                  11-point LMPC compliance check
                </div>

                <button 
                  className="btn-primary scan-action-btn" 
                  onClick={handleUpload}
                  disabled={!file || isUploading}
                >
                  {isUploading ? `PROCESSING [${uploadProgress}%]` : '3. Start Inspection'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
