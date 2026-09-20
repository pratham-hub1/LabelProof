import { useState, useEffect } from 'react'
import { Link, useLocation } from 'react-router-dom'
import './Navbar.css'

const navLinks = [
  { label: 'Overview', to: '/' },
  { label: 'History', to: '/history' },
  { label: 'Stats', to: '/stats' },
]

function Navbar() {
  const [scrolled, setScrolled] = useState(false)
  const location = useLocation()

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20)
    }
    window.addEventListener('scroll', handleScroll, { passive: true })
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  return (
    <nav className={`navbar ${scrolled ? 'scrolled' : ''}`}>
      <div className="navbar-inner">
        <Link className="navbar-brand" to="/">
          LABELPROOF
        </Link>

        <div className="navbar-links">
          {navLinks.map((link) => {
            const isActive = location.pathname === link.to;
            return (
              <Link 
                key={link.to} 
                className={`navbar-link ${isActive ? 'active' : ''}`} 
                to={link.to}
              >
                {link.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

export default Navbar
