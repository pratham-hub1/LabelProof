import './Hero.css'

function Hero() {
  return (
    <section className="hero">
      <div className="hero-content">
        <div className="hero-eyebrow">LabelProof — SIH26034</div>
        <h1 className="hero-headline">
          Compliance, decoded.
        </h1>
        <p className="hero-subtext">
          Turn packaged-product imagery into structured evidence
          and explainable compliance results.
        </p>
        <div className="hero-actions">
          <button className="hero-btn-primary" type="button">
            Start Scanning
          </button>
          <a className="hero-btn-secondary" href="#how-it-works">
            Explore the technology
          </a>
        </div>
      </div>
    </section>
  )
}

export default Hero
