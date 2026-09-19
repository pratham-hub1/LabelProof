import { useNavigate } from 'react-router-dom'
import './Hero.css'

function Hero() {
  const navigate = useNavigate()

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
          <button
            className="hero-btn-primary"
            type="button"
            onClick={() => navigate('/scan')}
          >
            Start Scanning
          </button>
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
