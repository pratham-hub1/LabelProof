import { useState, useRef, useEffect } from 'react';
import './EvidenceViewer.css';

interface EvidenceViewerProps {
  imageUrl: string;
  originalWidth: number;
  originalHeight: number;
  boxes: Array<{
    id: string;
    box: [number, number, number, number];
    label?: string;
    color?: string;
  }>;
}

export default function EvidenceViewer({ imageUrl, originalWidth, originalHeight, boxes }: EvidenceViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const [scale, setScale] = useState({ scaleX: 1, scaleY: 1 });

  useEffect(() => {
    const handleResize = () => {
      if (imgRef.current && originalWidth > 0 && originalHeight > 0) {
        const rect = imgRef.current.getBoundingClientRect();
        setScale({
          scaleX: rect.width / originalWidth,
          scaleY: rect.height / originalHeight,
        });
      }
    };

    // Run on mount, window resize, and image load
    window.addEventListener('resize', handleResize);
    handleResize();

    return () => window.removeEventListener('resize', handleResize);
  }, [originalWidth, originalHeight]);

  return (
    <div className="evidence-viewer" ref={containerRef}>
      <div className="evidence-image-container">
        <img 
          ref={imgRef}
          src={imageUrl} 
          alt="Evidence" 
          className="evidence-image"
          onLoad={() => {
            // Trigger a resize calculation when the image finally loads
            if (imgRef.current && originalWidth > 0 && originalHeight > 0) {
              const rect = imgRef.current.getBoundingClientRect();
              setScale({
                scaleX: rect.width / originalWidth,
                scaleY: rect.height / originalHeight,
              });
            }
          }}
        />
        {boxes.map((b) => {
          const [x1, y1, x2, y2] = b.box;
          const left = x1 * scale.scaleX;
          const top = y1 * scale.scaleY;
          const width = (x2 - x1) * scale.scaleX;
          const height = (y2 - y1) * scale.scaleY;

          return (
            <div 
              key={b.id}
              className="evidence-box"
              style={{
                left: `${left}px`,
                top: `${top}px`,
                width: `${width}px`,
                height: `${height}px`,
                borderColor: b.color || 'var(--color-accent)',
              }}
            >
              {b.label && (
                <div 
                  className="evidence-box-label"
                  style={{ backgroundColor: b.color || 'var(--color-accent)' }}
                >
                  {b.label}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
