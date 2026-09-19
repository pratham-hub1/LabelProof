import { Link, useNavigate } from 'react-router-dom'
import './Navbar.css'

const navLinks = [
  { label: 'Overview', to: '/' },
  { label: 'How it works', to: '/#how-it-works' },
  { label: 'Reports', to: '#', isPlaceholder: true },
  { label: 'History', to: '/history' },
]

function Navbar() {
  const navigate = useNavigate()

  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <Link className="navbar-brand" to="/">
          LABELCHECK
        </Link>

        <div className="navbar-links">
          {navLinks.map((link) => (
            <Link 
              key={link.label} 
              className="navbar-link" 
              to={link.to}
              onClick={link.isPlaceholder ? (e) => e.preventDefault() : undefined}
              style={link.isPlaceholder ? { cursor: 'not-allowed', opacity: 0.5 } : {}}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <button 
          className="navbar-cta" 
          type="button" 
          onClick={() => navigate('/scan')}
        >
          Scan a package
        </button>
      </div>
    </nav>
  )
}

export default Navbar
