<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCircuitPath } from '~/lib/api'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  telemetry: CarDataRecord | null
  teamColor?: string
  driverAcronym?: string
}>()

type CircuitPoint = { x: number; y: number; sector: number }

const circuitPath = ref<CircuitPoint[]>([])

onMounted(async () => {
  try {
    // Keep attempting to fetch until successful
    const path = await getCircuitPath(9161) as Array<
      Partial<CircuitPoint> & { x: number; y: number }
    >
    circuitPath.value = path.map(point => ({
      x: point.x,
      y: point.y,
      sector: point.sector ?? 0
    }))
  } catch (e) {
    console.error("Failed to load Singapore track map")
  }
})

const hasRenderableTrack = computed(() => circuitPath.value.length > 0)

const renderTrackPath = computed(() => {
  return circuitPath.value
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

const createSectorPoints = (sector: number) => {
  const points = renderTrackPath.value

  return points
    .flatMap((point, index) => {
      if (point.sector !== sector) {
        return []
      }

      const sectorPoints = [`${point.x},${point.y}`]
      const nextPoint = points[index + 1]
      if (nextPoint && nextPoint.sector !== sector) {
        sectorPoints.push(`${nextPoint.x},${nextPoint.y}`)
      }

      return sectorPoints
    })
    .join(' ')
}

const sector1Points = computed(() => createSectorPoints(1))
const sector2Points = computed(() => createSectorPoints(2))
const sector3Points = computed(() => createSectorPoints(3))

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
  <div class="bg-[#1e1e28] rounded-xl p-4 border border-white/5 shadow-lg flex flex-col h-[320px] w-full relative overflow-hidden">
    <h2 class="absolute top-6 left-6 text-sm text-gray-400 uppercase tracking-widest font-bold z-10">Track Map</h2>
    
    <svg
      v-if="hasRenderableTrack"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      class="w-full h-full transform -scale-y-100 flex-1 mt-4"
    >
      <!-- 1. Outer Border (Black) -->
      <polyline
        :points="circuitSvgPoints"
        fill="none"
        stroke="#0a0a0f"
        stroke-width="300"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- Sector 1 (Red) -->
      <polyline :points="sector1Points" fill="none" stroke="#e10600" stroke-width="150" stroke-linejoin="round" stroke-linecap="round" />
      <!-- Sector 2 (Cyan) -->
      <polyline :points="sector2Points" fill="none" stroke="#00a0d6" stroke-width="150" stroke-linejoin="round" stroke-linecap="round" />
      <!-- Sector 3 (Yellow) -->
      <polyline :points="sector3Points" fill="none" stroke="#fff200" stroke-width="150" stroke-linejoin="round" stroke-linecap="round" />

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
    <div v-else class="flex flex-col items-center justify-center h-full text-gray-500">
      <p class="text-xs font-bold uppercase tracking-widest">Loading Track Geometry...</p>
    </div>
  </div>
</template>
