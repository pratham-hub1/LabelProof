function SceneLighting() {
  return (
    <>
      <ambientLight intensity={0.4} />
      <directionalLight position={[5, 5, 5]} intensity={1.2} />
      <pointLight position={[-4, 2, -3]} intensity={1.5} color="#00d4ff" />
    </>
  )
}

export default SceneLighting
