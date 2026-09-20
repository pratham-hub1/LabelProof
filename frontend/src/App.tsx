import { Routes, Route, useLocation } from 'react-router-dom'
import { useState, useLayoutEffect } from 'react'
import Navbar from './components/Navbar'
import LandingPage from './pages/LandingPage'
import ScanPage from './pages/ScanPage'
import HistoryPage from './pages/HistoryPage'
import StatsPage from './pages/StatsPage'
import ReportPage from './pages/ReportPage'
import './App.css'

function App() {
  const location = useLocation()
  const isHome = location.pathname === '/'
  const [visible, setVisible] = useState(true)

  useLayoutEffect(() => {
    setVisible(false)
    window.scrollTo(0, 0)

    let frame2: number;
    const frame1 = requestAnimationFrame(() => {
      frame2 = requestAnimationFrame(() => {
        setVisible(true)
      })
    })

    return () => {
      cancelAnimationFrame(frame1)
      cancelAnimationFrame(frame2)
    }
  }, [location.pathname])

  return (
    <div className={`app ${!isHome ? 'functional-app' : ''}`}>
      <Navbar />
      <main className="main">
        <div 
          className={`route-transition-surface ${visible ? 'is-visible' : ''} ${isHome ? 'home-route' : 'functional-route'}`}
        >
          <Routes location={location}>
            <Route path="/" element={<LandingPage />} />
            <Route path="/scan" element={<ScanPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/report/:scanId" element={<ReportPage />} />
          </Routes>
        </div>
      </main>
    </div>
  )
}

export default App
