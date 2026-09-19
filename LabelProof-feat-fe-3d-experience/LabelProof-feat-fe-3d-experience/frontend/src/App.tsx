import Navbar from './components/Navbar'
import Hero from './components/Hero'
import PackageScrollSequence from './components/cinematic/PackageScrollSequence'
import './App.css'

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="main">
        <Hero />
        <PackageScrollSequence />
      </main>
    </div>
  )
}

export default App
