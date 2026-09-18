import { Canvas } from '@react-three/fiber'
import PackageModel from './PackageModel'
import SceneLighting from './SceneLighting'
import './PackageScene.css'

function PackageScene() {
  return (
    <section className="scene-section">
      <div className="scene-container">
        <Canvas camera={{ position: [0, 0, 5], fov: 50 }}>
          <SceneLighting />
          <PackageModel />
        </Canvas>
      </div>
    </section>
  )
}

export default PackageScene
