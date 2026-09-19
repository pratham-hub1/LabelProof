import { useState, useEffect } from 'react'
import './Navbar.css'

const navLinks = [
  { label: 'Overview', href: '#overview' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Reports', href: '#reports' },
  { label: 'History', href: '#history' },
]

function Navbar() {
  const [scrolled, setScrolled] = useState(false)

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
        <a className="navbar-brand" href="/">
          LABELPROOF
        </a>

        <div className="navbar-links">
          {navLinks.map((link) => (
            <a key={link.href} className="navbar-link" href={link.href}>
              {link.label}
            </a>
          ))}
        </div>

        <button className="navbar-cta" type="button">
          Scan a package
        </button>
      </div>
    </nav>
  )
}

export default Navbar
