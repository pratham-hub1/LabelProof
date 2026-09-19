import { useNavigate } from 'react-router-dom'
import './Hero.css'

function Hero() {
  const navigate = useNavigate()

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
            className="hero-btn-primary" 
            type="button"
            onClick={() => navigate('/scan')}
          >
            Scan a package
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
