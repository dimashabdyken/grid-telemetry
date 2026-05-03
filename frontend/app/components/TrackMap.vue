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
    const path = (await getCircuitPath(9161)) as any[]

    circuitPath.value = path.map((p) => {
      // Just use the real sector from backend, default to 1 if missing for safety
      return { x: p.x, y: p.y, sector: p.sector || 1 }
    })
  } catch {
    circuitPath.value = []
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

const fullTrackPoints = computed(() => {
  return renderTrackPath.value.map(point => `${point.x},${point.y}`).join(' ')
})

const getSectorPoints = (sector: number) => {
  const pts: string[] = []
  const path = circuitPath.value
  for (let i = 0; i < path.length; i++) {
    const point = path[i]
    if (!point || point.sector !== sector) {
      continue
    }

    pts.push(`${point.x},${point.y}`)
    const nextPoint = path[i + 1]
    const firstPoint = path[0]

    // Close gaps between different sectors
    if (nextPoint && nextPoint.sector !== sector) {
      pts.push(`${nextPoint.x},${nextPoint.y}`)
    }
    // Close the circuit loop
    if (i === path.length - 1 && firstPoint && firstPoint.sector !== sector) {
      pts.push(`${firstPoint.x},${firstPoint.y}`)
    }
  }
  return pts.join(' ')
}

const sector1Points = computed(() => getSectorPoints(1))
const sector2Points = computed(() => getSectorPoints(2))
const sector3Points = computed(() => getSectorPoints(3))

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
  <div class="relative h-full w-full">
    <svg
      v-if="hasRenderableTrack"
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      class="w-full h-full transform -scale-y-100"
    >
      <!-- 1. Outer Border (Black) -->
      <polyline
        :points="fullTrackPoints"
        fill="none"
        stroke="#0a0a0f"
        stroke-width="460"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- 2. Colored Sectors -->
      <polyline :points="sector1Points" fill="none" stroke="#e10600" stroke-width="150" stroke-linejoin="round" stroke-linecap="round" />
      <polyline :points="sector2Points" fill="none" stroke="#00a0d6" stroke-width="150" stroke-linejoin="round" stroke-linecap="round" />
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
      <p class="text-xs font-mono uppercase tracking-[0.2em]">Loading Track Geometry</p>
    </div>
  </div>
</template>
