import Navbar from './components/Navbar'
import Hero from './components/Hero'
import ThreeDPlaceholder from './components/ThreeDPlaceholder'
import './App.css'

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="main">
        <Hero />
        <ThreeDPlaceholder />
      </main>
    </div>
  )
}

export default App
