import './Navbar.css'

const navLinks = [
  { label: 'Overview', href: '#overview' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Reports', href: '#reports' },
  { label: 'History', href: '#history' },
]

function Navbar() {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <a className="navbar-brand" href="/">
          LABELCHECK
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
