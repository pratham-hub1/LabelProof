import { useRef } from 'react'
import { useFrame } from '@react-three/fiber'
import { RoundedBox, Edges } from '@react-three/drei'
import type { Group } from 'three'

function PackageModel() {
  const groupRef = useRef<Group>(null)

  useFrame(({ clock }) => {
    if (!groupRef.current) return
    // Slow continuous rotation
    groupRef.current.rotation.y += 0.003
    // Subtle floating motion
    groupRef.current.position.y = Math.sin(clock.elapsedTime * 0.8) * 0.08
  })

  return (
    <group ref={groupRef}>
      <RoundedBox args={[1.6, 2.2, 0.7]} radius={0.06} smoothness={4}>
        <meshStandardMaterial
          color="#2a2a2a"
          roughness={0.5}
          metalness={0.5}
        />
        <Edges color="#00d4ff" threshold={15} />
      </RoundedBox>
    </group>
  )
}

export default PackageModel
