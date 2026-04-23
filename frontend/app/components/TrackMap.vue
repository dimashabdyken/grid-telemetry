<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCircuitPath } from '~/lib/api'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  telemetry: CarDataRecord | null
  teamColor?: string
}>()

const circuitPath = ref<{ x: number; y: number }[]>([])

onMounted(async () => {
  try {
    circuitPath.value = await getCircuitPath(9161)
  } catch {
    circuitPath.value = []
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
</script>

<template>
  <div class="bg-[#1e1e28] rounded-xl p-4 border border-white/5 shadow-lg flex flex-col h-[280px] md:h-[320px] relative">
    <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">TRACK MAP</h2>

    <svg
      :viewBox="viewBox"
      preserveAspectRatio="xMidYMid meet"
      class="w-full h-full transform -scale-y-100 flex-1 mt-2"
    >
      <!-- 1. Outer Track Border (Thick Dark/Black Outline) -->
      <polyline
        :points="circuitSvgPoints"
        fill="none"
        stroke="#0a0a0f"
        stroke-width="1200"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- 2. Inner Racing Line (Solid Light Gray/White) -->
      <polyline
        :points="circuitSvgPoints"
        fill="none"
        stroke="#e2e8f0"
        stroke-width="400"
        stroke-linejoin="round"
        stroke-linecap="round"
      />

      <!-- 3. Car Dot (Properly scaled to fit inside the track) -->
      <g
        v-if="props.telemetry?.x !== undefined && props.telemetry?.y !== undefined"
        class="transition-all duration-200"
      >
        <circle
          :cx="props.telemetry.x"
          :cy="props.telemetry.y"
          r="350"
          :fill="carColor"
          stroke="#ffffff"
          stroke-width="100"
        />
      </g>
    </svg>
  </div>
</template>
