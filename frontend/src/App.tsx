import Navbar from './components/Navbar'
import Hero from './components/Hero'
import PackageScene from './components/scene/PackageScene'
import './App.css'

function App() {
  return (
    <div className="app">
      <Navbar />
      <main className="main">
        <Hero />
        <PackageScene />
      </main>
    </div>
  )
}

export default App
