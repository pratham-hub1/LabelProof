import { useEffect, useRef, useState } from 'react'
import './PackageScrollSequence.css'
import CinematicStory from './CinematicStory'
import InspectionOverlay from './InspectionOverlay'
import CinematicNavigation from './CinematicNavigation'

const TOTAL_FRAMES = 300
const FRAME_PREFIX = '/frames/package/ezgif-frame-'

function getFrameUrl(index: number) {
  const fileNumber = (index + 1).toString().padStart(3, '0')
  return `${FRAME_PREFIX}${fileNumber}.png`
}

export default function PackageScrollSequence() {
  const sectionRef = useRef<HTMLDivElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  
  const imagesRef = useRef<(HTMLImageElement | null)[]>(new Array(TOTAL_FRAMES).fill(null))
  const activeFrameRef = useRef(0)
  
  // Expose scroll progress to UI overlay layers
  const [progress, setProgress] = useState(0)

  // Optimization: render only when needed
  const renderFrame = (index: number) => {
    if (!canvasRef.current) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Find closest loaded frame
    let renderIndex = index
    if (!imagesRef.current[index]) {
      let fallback = 0
      for (let i = index; i >= 0; i--) {
        if (imagesRef.current[i]) {
          fallback = i
          break
        }
      }
      renderIndex = fallback
    }

    const img = imagesRef.current[renderIndex]
    if (!img) return

    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    
    // Explicit sizing for canvas context to prevent blur
    const targetW = Math.max(1, Math.round(rect.width * dpr))
    const targetH = Math.max(1, Math.round(rect.height * dpr))

    if (canvas.width !== targetW || canvas.height !== targetH) {
      canvas.width = targetW
      canvas.height = targetH
    }

    // High quality rendering
    ctx.imageSmoothingEnabled = true;
    ctx.imageSmoothingQuality = 'high';

    // Clear background
    ctx.fillStyle = '#050505'
    ctx.fillRect(0, 0, canvas.width, canvas.height)

    // Calculate containment
    const hRatio = canvas.width / img.width
    const vRatio = canvas.height / img.height
    const ratio = Math.min(hRatio, vRatio)

    const drawW = img.width * ratio
    const drawH = img.height * ratio

    const dx = (canvas.width - drawW) / 2
    const dy = (canvas.height - drawH) / 2

    ctx.drawImage(img, 0, 0, img.width, img.height, dx, dy, drawW, drawH)
  }

  useEffect(() => {
    let isComponentMounted = true;

    // Load a single frame
    const loadFrame = (index: number): Promise<void> => {
      return new Promise((resolve) => {
        if (imagesRef.current[index]) return resolve()
        
        const img = new Image()
        img.src = getFrameUrl(index)
        img.onload = () => {
          if (!isComponentMounted) return resolve()
          imagesRef.current[index] = img
          
          // Re-render if it might improve the currently displayed frame
          requestAnimationFrame(() => {
             if (isComponentMounted) renderFrame(activeFrameRef.current)
          })
          resolve()
        }
        img.onerror = () => resolve() // Fail gracefully
      })
    }

    const preloadSequence = async () => {
      // 1. Critical frames first (await them to ensure we have something)
      await loadFrame(0)
      if (!isComponentMounted) return
      renderFrame(0)
      
      await loadFrame(TOTAL_FRAMES - 1)
      await loadFrame(Math.floor(TOTAL_FRAMES * 0.25))
      await loadFrame(Math.floor(TOTAL_FRAMES * 0.5))
      await loadFrame(Math.floor(TOTAL_FRAMES * 0.75))
      
      // 2. Load the rest progressively (WITHOUT blocking await so they load much faster)
      for (let i = 1; i < TOTAL_FRAMES - 1; i++) {
        if (!isComponentMounted) break
        if (!imagesRef.current[i]) {
          loadFrame(i) // Non-blocking!
        }
      }
    }
    
    preloadSequence()

    const updateScrollState = () => {
      if (!sectionRef.current) return

      // 4. SCROLL PROGRESS
      const section = sectionRef.current
      const rect = section.getBoundingClientRect()
      
      // Get the true scroll top whether it's document scrolling or body scrolling
      const scrollTop = document.scrollingElement ? document.scrollingElement.scrollTop : window.scrollY;
      
      const sectionTop = rect.top + scrollTop
      const sectionHeight = section.offsetHeight
      const viewportHeight = window.innerHeight
      const scrollDistance = sectionHeight - viewportHeight

      let currentProgress = 0
      if (scrollDistance > 0) {
        currentProgress = (scrollTop - sectionTop) / scrollDistance
      }
      
      currentProgress = Math.max(0, Math.min(1, currentProgress))
      
      // Sync UI progress
      setProgress(currentProgress)

      const targetFrame = Math.round(currentProgress * (TOTAL_FRAMES - 1))
      
      // Update Canvas State
      if (targetFrame !== activeFrameRef.current) {
        activeFrameRef.current = targetFrame
        renderFrame(targetFrame)
      }
    }

    let scrollTicking = false
    const handleScroll = () => {
      if (!scrollTicking) {
        requestAnimationFrame(() => {
          updateScrollState()
          scrollTicking = false
        })
        scrollTicking = true
      }
    }

    let resizeTicking = false
    const handleResize = () => {
      if (!resizeTicking) {
        requestAnimationFrame(() => {
          renderFrame(activeFrameRef.current)
          updateScrollState()
          resizeTicking = false
        })
        resizeTicking = true
      }
    }

    window.addEventListener('scroll', handleScroll, { passive: true })
    window.addEventListener('resize', handleResize, { passive: true })
    
    // Initial calculation after a slight delay to ensure layout is complete
    setTimeout(() => {
      if (isComponentMounted) {
        handleResize()
        updateScrollState()
      }
    }, 100)
    
    // Fallback: update again after 1s just in case fonts or other elements shift layout
    setTimeout(() => {
      if (isComponentMounted) {
        updateScrollState()
      }
    }, 1000)

    return () => {
      isComponentMounted = false
      window.removeEventListener('scroll', handleScroll)
      window.removeEventListener('resize', handleResize)
    }
  }, [])

  // Derived camera illusion based on progress
  let canvasTransform = 'scale(1) translate3d(0,0,0) rotateZ(0deg)'
  if (progress < 0.15) {
     const local = progress / 0.15
     canvasTransform = `scale(${1 + local * 0.02}) translate3d(0,0,0) rotateZ(0deg)`
  } else if (progress < 0.30) {
     const local = (progress - 0.15) / 0.15
     const tilt = local * 1.5 // 0 to 1.5 deg
     canvasTransform = `scale(1.02) translate3d(0,0,0) rotateZ(${tilt}deg)`
  } else if (progress < 0.45) {
     canvasTransform = `scale(1.02) translate3d(0,0,0) rotateZ(1.5deg)`
  } else if (progress < 0.60) {
     const local = (progress - 0.45) / 0.15
     const driftX = Math.sin(local * Math.PI) * 20 // lateral drift up to 20px
     canvasTransform = `scale(1.02) translate3d(${driftX}px,0,0) rotateZ(1.5deg)`
  } else if (progress < 0.80) {
     const local = (progress - 0.60) / 0.20
     // tilt goes from 1.5 to -1.0
     const tilt = 1.5 - (local * 2.5) 
     canvasTransform = `scale(${1.02 - local * 0.02}) translate3d(0,0,0) rotateZ(${tilt}deg)`
  } else {
     const local = (progress - 0.80) / 0.20
     // tilt goes from -1.0 to 0
     const tilt = -1.0 * (1 - local)
     canvasTransform = `scale(1) translate3d(0,0,0) rotateZ(${tilt}deg)`
  }

  // Calculate ambient glow opacities
  const scanOpacity = (progress > 0.15 && progress < 0.30) ? Math.sin(((progress - 0.15) / 0.15) * Math.PI) : 0;
  const recognizeOpacity = (progress >= 0.30 && progress < 0.45) ? Math.sin(((progress - 0.30) / 0.15) * Math.PI) : 0;
  const inspectOpacity = (progress >= 0.45 && progress < 0.60) ? Math.sin(((progress - 0.45) / 0.15) * Math.PI) : 0;
  
  // Transition into next section (darken package slightly at the very end)
  const endDarkenOpacity = progress >= 0.90 ? (progress - 0.90) * 8 : 0; // reaches 0.8 opacity at 1.0

  return (
    <section 
      className="package-sequence" 
      ref={sectionRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '400vh',
        minHeight: '400vh',
        display: 'block' // guarantees it is not display: contents
      }}
    >
      <div 
        className="package-sequence-sticky"
        style={{
          position: 'sticky',
          top: 0,
          width: '100%',
          height: '100vh',
          minHeight: '100vh',
          overflow: 'hidden'
        }}
      >
        <div className="ambient-glow scan-glow" style={{ opacity: scanOpacity }} />
        <div className="ambient-glow recognize-glow" style={{ opacity: recognizeOpacity }} />
        <div className="ambient-glow inspect-glow" style={{ opacity: inspectOpacity }} />
        
        <canvas 
          ref={canvasRef} 
          className="package-sequence-canvas" 
          style={{ width: '100%', height: '100%', display: 'block', transform: canvasTransform }}
        />

        <div className="cinematic-darken-overlay" style={{ opacity: Math.min(0.8, endDarkenOpacity) }}></div>

        <InspectionOverlay progress={progress} />
        <CinematicStory progress={progress} />
        <CinematicNavigation progress={progress} />
      </div>
      <div className="cinematic-handoff-bridge"></div>
    </section>
  )
}
