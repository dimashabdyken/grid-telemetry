<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { getCircuitPath } from '~/lib/api'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  telemetry: CarDataRecord | null
  teamColor?: string
  driverAcronym?: string
}>()

const circuitPath = ref<{ x: number; y: number }[]>([])
const animatedIndex = ref(0)
let animationFrameId: number | null = null
let previousFrameTime = 0

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

const viewBox = computed(() => {
  if (!circuitPath.value.length) {
    return '-1000 -1000 2000 2000'
  }

  const xs = circuitPath.value.map(point => point.x)
  const ys = circuitPath.value.map(point => point.y)

  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  const padding = Math.max(maxX - minX, maxY - minY) * 0.10
  return `${minX - padding} ${minY - padding} ${(maxX - minX) + padding * 2} ${(maxY - minY) + padding * 2}`
})

const circuitSvgPoints = computed(() => {
  return circuitPath.value.map(point => `${point.x},${point.y}`).join(' ')
})

const carColor = computed(() => {
  return props.teamColor ? `#${props.teamColor.replace('#', '')}` : '#ffffff'
})

const fallbackTelemetryIndex = computed(() => {
  if (!circuitPath.value.length) {
    return -1
  }

  const rawId = Number(props.telemetry?._id)
  if (Number.isFinite(rawId)) {
    return Math.abs(Math.trunc(rawId)) % circuitPath.value.length
  }

  const timestamp = Date.parse(props.telemetry?.date ?? '')
  const tick = Number.isFinite(timestamp) ? Math.abs(Math.trunc(timestamp / 100)) : 0
  return tick % circuitPath.value.length
})

const snappedTelemetryIndex = computed(() => {
  if (!circuitPath.value.length) {
    return -1
  }

  const telemetryX = Number(props.telemetry?.x)
  const telemetryY = Number(props.telemetry?.y)
  const hasFiniteCoordinates = Number.isFinite(telemetryX) && Number.isFinite(telemetryY)
  if (!hasFiniteCoordinates) {
    return -1
  }

  // FastF1 fallbacks can emit (0, 0) when position is unavailable; ignore it.
  if (Math.abs(telemetryX) < 0.0001 && Math.abs(telemetryY) < 0.0001) {
    return -1
  }

  let nearestIndex = 0
  let nearestDistance = Number.POSITIVE_INFINITY

  for (const [index, point] of circuitPath.value.entries()) {
    const dx = point.x - telemetryX
    const dy = point.y - telemetryY
    const distance = dx * dx + dy * dy
    if (distance < nearestDistance) {
      nearestDistance = distance
      nearestIndex = index
    }
  }

  return nearestIndex
})

const targetTelemetryIndex = computed(() => {
  return snappedTelemetryIndex.value >= 0
    ? snappedTelemetryIndex.value
    : fallbackTelemetryIndex.value
})

const shortestCircularDelta = (from: number, to: number, size: number): number => {
  let delta = (to - from) % size
  if (delta > size / 2) {
    delta -= size
  }
  if (delta < -size / 2) {
    delta += size
  }
  return delta
}

const animateCarToTarget = (timestamp: number) => {
  if (!previousFrameTime) {
    previousFrameTime = timestamp
  }

  const deltaMs = Math.min(50, timestamp - previousFrameTime)
  const frameFactor = deltaMs / 16.67
  previousFrameTime = timestamp

  const size = circuitPath.value.length
  if (size === 0) {
    animationFrameId = requestAnimationFrame(animateCarToTarget)
    return
  }

  let target = targetTelemetryIndex.value
  const maxJump = Math.max(6, Math.floor(size * 0.02))

  if (target >= 0) {
    // Reject impossible jumps from noisy/misaligned coordinate snaps.
    const candidateDelta = shortestCircularDelta(animatedIndex.value, target, size)
    if (Math.abs(candidateDelta) > maxJump) {
      const fallbackTarget = fallbackTelemetryIndex.value
      const fallbackDelta = fallbackTarget >= 0
        ? shortestCircularDelta(animatedIndex.value, fallbackTarget, size)
        : Number.POSITIVE_INFINITY

      if (Number.isFinite(fallbackDelta) && Math.abs(fallbackDelta) <= maxJump) {
        target = fallbackTarget
      } else {
        target = (animatedIndex.value + Math.sign(candidateDelta) * maxJump + size) % size
      }
    }

    const delta = shortestCircularDelta(animatedIndex.value, target, size)
    const telemetrySpeed = Number(props.telemetry?.speed ?? 0)
    const normalizedSpeed = Number.isFinite(telemetrySpeed)
      ? Math.max(0, Math.min(telemetrySpeed, 340)) / 340
      : 0

    // Cap movement per frame so the marker follows telemetry instead of drifting ahead.
    const maxStep = (0.7 + normalizedSpeed * 1.8) * frameFactor
    const step = Math.max(-maxStep, Math.min(maxStep, delta))
    animatedIndex.value = (animatedIndex.value + step + size) % size
  } else {
    // No target available: keep tiny movement so UI does not appear frozen.
    const cruiseStep = 0.03 * frameFactor
    animatedIndex.value = (animatedIndex.value + cruiseStep + size) % size
  }

  animationFrameId = requestAnimationFrame(animateCarToTarget)
}

watch(
  [() => circuitPath.value.length, () => targetTelemetryIndex.value],
  ([length, target], [previousLength]) => {
    if (!length) {
      animatedIndex.value = 0
      return
    }

    // When path first loads (previousLength was 0 or falsy), jump to target or start position
    if (!previousLength && length > 0) {
      animatedIndex.value = target >= 0 ? target : 0
      return
    }

    // If we have a valid target and animatedIndex is at an invalid state, initialize it
    if (target >= 0 && !Number.isFinite(animatedIndex.value)) {
      animatedIndex.value = target
    }
  },
  { immediate: true }
)

const carPoint = computed(() => {
  const path = circuitPath.value
  if (!path.length) {
    return null
  }

  const safeIndex = ((animatedIndex.value % path.length) + path.length) % path.length
  const baseIndex = Math.floor(safeIndex)
  const nextIndex = (baseIndex + 1) % path.length
  const interpolation = safeIndex - baseIndex

  const current = path[baseIndex]
  const next = path[nextIndex]
  if (!current || !next) {
    return null
  }

  return {
    x: current.x + (next.x - current.x) * interpolation,
    y: current.y + (next.y - current.y) * interpolation,
  }
})

onMounted(() => {
  animationFrameId = requestAnimationFrame(animateCarToTarget)
})

onBeforeUnmount(() => {
  if (animationFrameId !== null) {
    cancelAnimationFrame(animationFrameId)
    animationFrameId = null
  }
  previousFrameTime = 0
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
        :cx="carPoint.x"
        :cy="carPoint.y"
        r="120"
        :fill="carColor"
        stroke="#ffffff"
        stroke-width="40"
        class="transition-all duration-[100ms] ease-linear drop-shadow-[0_0_6px_rgba(255,255,255,0.4)]"
      />
    </svg>
  </div>
</template>