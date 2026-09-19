import './InspectionOverlay.css';

interface InspectionOverlayProps {
  progress: number;
}

export default function InspectionOverlay({ progress }: InspectionOverlayProps) {
  // Mostly visible during 0.40 -> 0.65
  let opacity = 0;
  if (progress >= 0.40 && progress <= 0.60) {
    if (progress < 0.45) {
      opacity = (progress - 0.40) / 0.05;
    } else if (progress > 0.55) {
      opacity = (0.60 - progress) / 0.05;
    } else {
      opacity = 1;
    }
  }

  if (opacity <= 0.01) return null;

  return (
    <div className="inspection-overlay" style={{ opacity }}>
      {/* Technical Grid Background */}
      <div className="inspection-grid"></div>

      {/* Main scanning line sweeping down */}
      <div 
        className="scan-line" 
        style={{ top: `${(progress - 0.40) / 0.25 * 100}%` }}
      ></div>

      {/* Center Focus Brackets */}
      <div className="bracket bracket-tl"></div>
      <div className="bracket bracket-tr"></div>
      <div className="bracket bracket-bl"></div>
      <div className="bracket bracket-br"></div>

      {/* Subtle Data Labels connected to anchor dots */}
      {/* Target 1: Top Left */}
      <div className="target-point" style={{ top: '35%', left: '30%' }}>
        <div className="anchor-dot"></div>
        <div className="connecting-line line-left"></div>
        <div className="target-label">
          <span className="coord">X:142 Y:088</span>
          <span className="desc">MFR_BLOCK</span>
        </div>
      </div>

      {/* Target 2: Top Right */}
      <div className="target-point" style={{ top: '42%', left: '65%' }}>
        <div className="anchor-dot"></div>
        <div className="connecting-line line-right"></div>
        <div className="target-label right">
          <span className="coord">X:492 Y:120</span>
          <span className="desc">NET_QTY</span>
        </div>
      </div>

      {/* Target 3: Bottom Center */}
      <div className="target-point" style={{ top: '65%', left: '48%' }}>
        <div className="anchor-dot"></div>
        <div className="connecting-line line-left"></div>
        <div className="target-label">
          <span className="coord">X:350 Y:410</span>
          <span className="desc">PRICE_TAG</span>
        </div>
      </div>
    </div>
  );
}