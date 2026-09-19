import './CinematicStory.css';

interface CinematicStoryProps {
  progress: number;
}

export default function CinematicStory({ progress }: CinematicStoryProps) {
  // Helper to calculate opacity and transform based on progress window
  const getStyle = (start: number, end: number) => {
    // Extend the end slightly so it doesn't blink out exactly at boundary
    const effectiveEnd = end === 1.0 ? 1.0 : end + 0.02;
    if (progress < start || progress > effectiveEnd) {
      return { opacity: 0, transform: 'translateY(20px)', pointerEvents: 'none' as const };
    }
    
    const range = effectiveEnd - start;
    const local = (progress - start) / range;
    
    // Fade in first 15% of the active range, fade out last 15%
    let opacity = 1;
    if (local < 0.15) {
      opacity = local / 0.15;
    } else if (local > 0.85) {
      opacity = (1 - local) / 0.15;
    }
    
    // Slow drift upwards
    const translateY = 20 - (local * 40); // 20px to -20px
    
    return {
      opacity,
      transform: `translateY(${translateY}px)`,
      pointerEvents: opacity > 0.5 ? 'auto' as const : 'none' as const
    };
  };

  return (
    <div className="cinematic-story-container">
      {/* 0-15%: HERO */}
      <div className="story-block hero-block" style={getStyle(0, 0.15)}>
        <div className="story-eyebrow">PACKAGED-COMMODITY INTELLIGENCE</div>
        <h2 className="story-heading">Every package carries information.</h2>
        <p className="story-supporting">LabelProof turns packaging information into structured compliance intelligence.</p>
      </div>

      {/* 15-30%: SCAN */}
      <div className="story-block side-block" style={getStyle(0.15, 0.30)}>
        <div className="story-eyebrow" style={{ color: 'rgba(255, 80, 80, 0.8)' }}>01 / SCAN</div>
        <h2 className="story-heading">Start with the surface.</h2>
        <p className="story-supporting">Identify the package before examining what it declares.</p>
      </div>

      {/* 30-45%: RECOGNITION */}
      <div className="story-block side-block" style={getStyle(0.30, 0.45)}>
        <div className="story-eyebrow" style={{ color: 'rgba(100, 255, 150, 0.8)' }}>02 / IDENTIFY</div>
        <h2 className="story-heading">Know what you're looking at.</h2>
        <p className="story-supporting">Packaging information becomes structured input for deeper inspection.</p>
      </div>

      {/* 45-60%: INSPECTION */}
      <div className="story-block side-block inspect-text" style={getStyle(0.45, 0.60)}>
        <div className="story-eyebrow" style={{ color: 'rgba(100, 200, 255, 0.8)' }}>03 / INSPECT</div>
        <h2 className="story-heading">Read beyond the surface.</h2>
        <p className="story-supporting">Key declaration regions are examined for the information a compliant package is expected to carry.</p>
      </div>

      {/* 60-80%: STRUCTURAL REVEAL */}
      <div className="story-block side-block" style={getStyle(0.60, 0.80)}>
        <div className="story-eyebrow">04 / ANALYZE</div>
        <h2 className="story-heading">Every detail matters.</h2>
        <p className="story-supporting">Understanding the package means understanding the information it presents.</p>
      </div>

      {/* 94-100%: EXPLODED STATE (After Callouts) */}
      <div className="story-block exploded-block" style={getStyle(0.94, 1.0)}>
        <div className="story-eyebrow">05 / REVEAL</div>
        <h2 className="story-heading large">From label to compliance.</h2>
        <p className="story-supporting">Structured evidence for a clearer view of packaged-commodity requirements.</p>
        <div className="story-transition-cue">
          Inspect a real package
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" style={{ marginLeft: '8px' }}>
            <line x1="5" y1="12" x2="19" y2="12"></line>
            <polyline points="12 5 19 12 12 19"></polyline>
          </svg>
        </div>
        <div className="transition-line-down"></div>
      </div>
    </div>
  );
}