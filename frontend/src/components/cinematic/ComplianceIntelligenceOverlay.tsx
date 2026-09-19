import './ComplianceIntelligenceOverlay.css';

interface ComplianceIntelligenceOverlayProps {
  progress: number;
}

export default function ComplianceIntelligenceOverlay({ progress }: ComplianceIntelligenceOverlayProps) {
  // Global visibility window
  const isVisible = progress > 0.78 && progress < 0.95;

  // Fade out all callouts right before the end to return focus to the package
  const globalFadeOut = progress >= 0.92 ? Math.max(0, 1 - (progress - 0.92) / 0.02) : 1;

  const getCalloutStyle = (appearAt: number) => {
    if (!isVisible || progress < appearAt) {
      return { opacity: 0, transform: 'translateY(10px) scale(0.95)' };
    }
    
    // Fade in gracefully over 0.02 progress (e.g. 80% to 82%)
    let opacity = Math.min(1, (progress - appearAt) / 0.02);
    opacity *= globalFadeOut;
    
    // Very subtle upward drift and scale up upon appearing
    const local = Math.min(1, (progress - appearAt) / 0.02);
    const translate = 10 * (1 - local);
    const scale = 0.95 + (0.05 * local);

    return {
      opacity,
      transform: `translateY(${translate}px) scale(${scale})`,
    };
  };

  if (!isVisible) return null;

  return (
    <div className="compliance-intelligence-overlay">
       
       {/* 1. IDENTITY (Left) */}
       <div className="intelligence-callout callout-left callout-identity" style={getCalloutStyle(0.80)}>
         <div className="anchor-dot"></div>
         <div className="connector-line"></div>
         <div className="callout-label">IDENTITY</div>
       </div>

       {/* 2. QUANTITY (Right) */}
       <div className="intelligence-callout callout-right callout-quantity" style={getCalloutStyle(0.80)}>
         <div className="anchor-dot"></div>
         <div className="connector-line"></div>
         <div className="callout-label">QUANTITY</div>
       </div>

       {/* 3. PRICE (Right) */}
       <div className="intelligence-callout callout-right callout-price" style={getCalloutStyle(0.84)}>
         <div className="anchor-dot"></div>
         <div className="connector-line"></div>
         <div className="callout-label">PRICE</div>
       </div>

       {/* 4. DATE (Left) */}
       <div className="intelligence-callout callout-left callout-date" style={getCalloutStyle(0.84)}>
         <div className="anchor-dot"></div>
         <div className="connector-line"></div>
         <div className="callout-label">DATE</div>
       </div>

       {/* 5. CONSUMER CARE (Left) */}
       <div className="intelligence-callout callout-left callout-care" style={getCalloutStyle(0.88)}>
         <div className="anchor-dot"></div>
         <div className="connector-line"></div>
         <div className="callout-label">CONSUMER CARE</div>
       </div>

       {/* 6. DECLARATIONS (Right) */}
       <div className="intelligence-callout callout-right callout-declarations" style={getCalloutStyle(0.88)}>
         <div className="anchor-dot"></div>
         <div className="connector-line"></div>
         <div className="callout-label">DECLARATIONS</div>
       </div>

    </div>
  );
}
