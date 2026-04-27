<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCircuitPath } from '~/lib/api'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  telemetry: CarDataRecord | null
  teamColor?: string
  driverAcronym?: string
}>()

const circuitPath = ref<{ x: number; y: number }[]>([])

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

const carPoint = computed(() => {
  if (props.telemetry?.x != null && props.telemetry?.y != null && props.telemetry.x !== 0 && props.telemetry.y !== 0) {
    return { x: props.telemetry.x, y: props.telemetry.y }
  }

  return null
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
        r="250"
        :fill="carColor"
        stroke="#ffffff"
        stroke-width="80"
        class="drop-shadow-[0_0_8px_rgba(255,255,255,0.4)]"
      />
    </svg>
  </div>
</template>