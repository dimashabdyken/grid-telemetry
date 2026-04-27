<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useSpring } from '@vueuse/motion'
import { getCircuitPath } from '~/lib/api'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  telemetry: CarDataRecord | null
  teamColor?: string
  driverAcronym?: string
}>()

const circuitPath = ref<{ x: number; y: number }[]>([])
const targetX = ref(0)
const targetY = ref(0)
const hasInitializedTarget = ref(false)
const lastTrackIndex = ref<number | null>(null)
const springValues = reactive({ x: 0, y: 0 })
// stiffness: speed of the spring, damping: resistance (prevents bouncing), mass: inertia
const spring = useSpring(springValues, { stiffness: 40, damping: 28, mass: 1.2 })
const springPosition = spring.values as Record<string, number>
const smoothX = computed(() => Number(springPosition.x ?? targetX.value))
const smoothY = computed(() => Number(springPosition.y ?? targetY.value))

// Generate a synthetic circular track for fallback/demo mode
const generateSyntheticTrack = (): { x: number; y: number }[] => {
  const points: { x: number; y: number }[] = []
  const numPoints = 500
  const radiusX = 800
  const radiusY = 600
  const centerX = 0
  const centerY = 0

  for (let i = 0; i < numPoints; i++) {
    const angle = (i / numPoints) * Math.PI * 2
    points.push({
      x: centerX + radiusX * Math.cos(angle),
      y: centerY + radiusY * Math.sin(angle)
    })
  }
  return points
}

onMounted(async () => {
  try {
    const path = await getCircuitPath(9161)
    circuitPath.value = path && path.length > 0 ? path : generateSyntheticTrack()
  } catch {
    circuitPath.value = generateSyntheticTrack()
  }
})

const hasRenderableTrack = computed(() => {
  const path = circuitPath.value
  if (path.length < 20) {
    return false
  }

  const xs = path.map(point => point.x)
  const ys = path.map(point => point.y)
  const xSpan = Math.max(...xs) - Math.min(...xs)
  const ySpan = Math.max(...ys) - Math.min(...ys)

  return xSpan > 1e-3 || ySpan > 1e-3
})

const renderTrackPath = computed(() => {
  return hasRenderableTrack.value ? circuitPath.value : generateSyntheticTrack()
})

const viewBox = computed(() => {
  if (!renderTrackPath.value.length) {
    return '-1000 -1000 2000 2000'
  }

  const xs = renderTrackPath.value.map(point => point.x)
  const ys = renderTrackPath.value.map(point => point.y)

  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  const padding = Math.max(maxX - minX, maxY - minY) * 0.10
  return `${minX - padding} ${minY - padding} ${(maxX - minX) + padding * 2} ${(maxY - minY) + padding * 2}`
})

const circuitSvgPoints = computed(() => {
  return renderTrackPath.value.map(point => `${point.x},${point.y}`).join(' ')
})

const carColor = computed(() => {
  return props.teamColor ? `#${props.teamColor.replace('#', '')}` : '#ffffff'
})

const maxStepPerTick = computed(() => {
  if (!renderTrackPath.value.length) {
    return 120
  }

  const xs = renderTrackPath.value.map(point => point.x)
  const ys = renderTrackPath.value.map(point => point.y)
  const xSpan = Math.max(...xs) - Math.min(...xs)
  const ySpan = Math.max(...ys) - Math.min(...ys)
  const diagonal = Math.hypot(xSpan, ySpan)

  return Math.min(80, Math.max(20, diagonal * 0.015))
})

const trackSnapMaxDistance = computed(() => {
  if (!renderTrackPath.value.length) {
    return 260
  }

  const xs = renderTrackPath.value.map(point => point.x)
  const ys = renderTrackPath.value.map(point => point.y)
  const diagonal = Math.hypot(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys))
  return Math.max(220, diagonal * 0.2)
})

const indexStepPerTick = computed(() => {
  const path = renderTrackPath.value
  if (!path.length) {
    return 12
  }

  // Keep movement smooth while preserving curvature in tight sections.
  return Math.max(2, Math.min(8, Math.floor(path.length / 600)))
})

const circularDistance = (from: number, to: number, size: number): number => {
  const raw = ((to - from) % size + size) % size
  return raw
}

const circularIndex = (index: number, size: number): number => {
  return ((index % size) + size) % size
}

const projectToTrackPoint = (x: number, y: number): { x: number; y: number; index: number | null } => {
  const path = renderTrackPath.value
  if (path.length < 20) {
    return { x, y, index: null }
  }

  let bestIndex = -1
  let bestScore = Number.POSITIVE_INFINITY
  let bestDistanceSq = Number.POSITIVE_INFINITY

  const previousIndex = lastTrackIndex.value
  if (previousIndex !== null) {
    // Prefer forward progress with a tiny backward allowance for noisy samples.
    const backwardAllowance = 10
    const forwardWindow = 60

    for (let offset = -backwardAllowance; offset <= forwardWindow; offset++) {
      const i = circularIndex(previousIndex + offset, path.length)
      const point = path[i]
      if (!point) {
        continue
      }

      const dx = point.x - x
      const dy = point.y - y
      const distanceSq = dx * dx + dy * dy

      // Strongly penalize backward jumps to avoid snapping to nearby parallel segments.
      const directionPenalty = offset < 0 ? 800 : 0
      const score = distanceSq + directionPenalty

      if (score < bestScore) {
        bestScore = score
        bestDistanceSq = distanceSq
        bestIndex = i
      }
    }

    // If local forward-biased search fails, fall back to full-track nearest lookup.
    if (bestIndex < 0) {
      for (let i = 0; i < path.length; i++) {
        const point = path[i]
        if (!point) {
          continue
        }
        const dx = point.x - x
        const dy = point.y - y
        const distanceSq = dx * dx + dy * dy
        if (distanceSq < bestDistanceSq) {
          bestDistanceSq = distanceSq
          bestScore = distanceSq
          bestIndex = i
        }
      }
    }
  } else {
    for (let i = 0; i < path.length; i++) {
      const point = path[i]
      if (!point) {
        continue
      }
      const dx = point.x - x
      const dy = point.y - y
      const distanceSq = dx * dx + dy * dy
      if (distanceSq < bestScore) {
        bestScore = distanceSq
        bestDistanceSq = distanceSq
        bestIndex = i
      }
    }
  }

  if (bestIndex < 0) {
    return { x, y, index: null }
  }

  const snapped = path[bestIndex]
  const snappedDistance = Math.sqrt(bestDistanceSq)

  // If telemetry is clearly too far from the track envelope, keep the raw point.
  if (!snapped || snappedDistance > trackSnapMaxDistance.value) {
    return { x, y, index: null }
  }

  return { x: snapped.x, y: snapped.y, index: bestIndex }
}

watch(
  () => props.telemetry,
  (newVal) => {
    const rawX = Number(newVal?.x)
    const rawY = Number(newVal?.y)

    if (!Number.isFinite(rawX) || !Number.isFinite(rawY)) {
      return
    }

    const projected = projectToTrackPoint(rawX, rawY)
    let x = projected.x
    let y = projected.y

    const path = renderTrackPath.value
    const previousIndex = lastTrackIndex.value

    if (projected.index !== null && path.length > 0) {
      if (previousIndex !== null) {
        const forwardDelta = circularDistance(previousIndex, projected.index, path.length)

        // Ignore implausible index jumps that usually come from noisy nearest-point matches.
        const maxTrustedDelta = Math.max(60, Math.floor(path.length * 0.25))
        const trustedDelta = forwardDelta <= maxTrustedDelta ? forwardDelta : indexStepPerTick.value
        const step = Math.min(Math.max(1, trustedDelta), indexStepPerTick.value)
        const nextIndex = circularIndex(previousIndex + step, path.length)
        const nextPoint = path[nextIndex]
        if (nextPoint) {
          x = nextPoint.x
          y = nextPoint.y
          lastTrackIndex.value = nextIndex
        }
      } else {
        lastTrackIndex.value = projected.index
      }
    } else if (previousIndex !== null && path.length > 0) {
      // Keep marker on track when incoming point cannot be confidently snapped.
      const holdPoint = path[previousIndex]
      if (holdPoint) {
        x = holdPoint.x
        y = holdPoint.y
      }
    }

    if (Number.isFinite(x) && Number.isFinite(y)) {
      if (!hasInitializedTarget.value) {
        targetX.value = x
        targetY.value = y
        hasInitializedTarget.value = true
        return
      }

      const dx = x - targetX.value
      const dy = y - targetY.value
      const distance = Math.hypot(dx, dy)

      // Ignore tiny GPS jitter and cap larger jumps to avoid visible teleportation.
      if (distance < 1) {
        return
      }

      const cappedStep = Math.min(distance, maxStepPerTick.value)
      const ratio = cappedStep / distance

      targetX.value += dx * ratio
      targetY.value += dy * ratio
    }
  },
  { immediate: true },
)

watch(
  [targetX, targetY],
  ([x, y]) => {
    spring.set({ x, y })
  },
  { immediate: true },
)

const carPoint = computed(() => {
  if (!Number.isFinite(Number(props.telemetry?.x)) || !Number.isFinite(Number(props.telemetry?.y))) {
    return null
  }

  return {
    x: smoothX.value,
    y: smoothY.value,
  }
})
</script>

<template>
  <div class="bg-[#1e1e28] rounded-xl p-4 border border-white/5 shadow-lg flex flex-col h-[280px] md:h-[320px] relative overflow-hidden">
    <h2 class="absolute top-6 left-6 text-sm text-gray-400 uppercase tracking-widest font-bold z-10">Track Map</h2>
    
    <svg
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      class="w-full h-full transform -scale-y-100 flex-1 mt-4"
    >
      <!-- 1. Outer Border (Black) -->
      <polyline
        :points="circuitSvgPoints"
        fill="none"
        stroke="#0a0a0f"
        stroke-width="400"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- 2. Inner Track (Solid Red) -->
      <polyline
        :points="circuitSvgPoints"
        fill="none"
        stroke="#e10600"
        stroke-width="90"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- Driver Label -->
      <g v-if="carPoint && driverAcronym" :transform="`translate(${carPoint.x + 200}, ${carPoint.y}) scale(1, -1)`">
        <rect x="0" y="-80" width="380" height="160" rx="80" fill="#ffffff" />
        <rect x="0" y="-80" width="60" height="160" rx="30" :fill="carColor" />
        <text x="90" y="40" fill="#000000" font-size="120" font-weight="900" font-family="sans-serif">{{ driverAcronym }}</text>
      </g>

      <!-- Car Dot -->
      <circle
        v-if="carPoint"
        :cx="smoothX"
        :cy="smoothY"
        r="250"
        :fill="carColor"
        stroke="#ffffff"
        stroke-width="80"
        class="drop-shadow"
      />
    </svg>
  </div>
</template>