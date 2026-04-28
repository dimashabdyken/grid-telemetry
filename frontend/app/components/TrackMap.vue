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

onMounted(async () => {
  try {
    // Keep attempting to fetch until successful
    const path = await getCircuitPath(9161)
    circuitPath.value = path
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
