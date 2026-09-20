import './Hero.css'

function Hero() {
  return (
    <section className="hero">
      <div className="hero-content">
        <h1 className="hero-headline">
          Compliance, decoded.
        </h1>
        <p className="hero-subtext">
          Turn packaged-product imagery into structured evidence
          and explainable compliance results.
        </p>
        <div className="hero-actions">
          <button
            className="btn-secondary"
            type="button"
            onClick={() => {
              window.scrollTo({
                top: window.innerHeight * 0.9,
                behavior: 'smooth'
              })
            }}
          >
            Explore the technology
            <svg className="btn-arrow" width="12" height="12" viewBox="0 0 12 12" fill="none" style={{ marginLeft: '4px' }}>
              <path d="M6 1L11 6M11 6L6 11M11 6L0 6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="square" strokeLinejoin="miter"/>
            </svg>
          </button>
        </div>
      </div>
    </section>
  )
}

export default Hero
