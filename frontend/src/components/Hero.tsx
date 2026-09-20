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
            className="hero-btn-secondary"
            type="button"
            onClick={() => {
              window.scrollTo({
                top: window.innerHeight * 0.9,
                behavior: 'smooth'
              })
            }}
          >
            Explore the technology
          </button>
        </div>
      </div>
    </section>
  )
}

export default Hero
