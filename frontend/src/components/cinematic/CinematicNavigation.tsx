import './CinematicNavigation.css';

interface CinematicNavigationProps {
  progress: number;
}

export default function CinematicNavigation({ progress }: CinematicNavigationProps) {
  // Determine active chapter (0-based)
  let activeIndex = -1;
  if (progress >= 0.15 && progress < 0.30) activeIndex = 0; // SCAN
  else if (progress >= 0.30 && progress < 0.45) activeIndex = 1; // IDENTIFY
  else if (progress >= 0.45 && progress < 0.60) activeIndex = 2; // INSPECT
  else if (progress >= 0.60 && progress < 0.80) activeIndex = 3; // ANALYZE
  else if (progress >= 0.80) activeIndex = 4; // REVEAL

  const chapters = [
    { num: '01', label: 'SCAN' },
    { num: '02', label: 'IDENTIFY' },
    { num: '03', label: 'INSPECT' },
    { num: '04', label: 'ANALYZE' },
    { num: '05', label: 'REVEAL' }
  ];

  return (
    <div className="cinematic-navigation">
      <div className="nav-progress-track">
        <div 
          className="nav-progress-fill" 
          style={{ '--progress': progress } as React.CSSProperties}
        ></div>
      </div>
      
      <div className="nav-chapters">
        {chapters.map((chap, i) => (
          <div 
            key={chap.num} 
            className={`nav-chapter ${i === activeIndex ? 'active' : ''}`}
          >
            <span className="nav-num">{chap.num}</span>
            <span className="nav-label">{chap.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}