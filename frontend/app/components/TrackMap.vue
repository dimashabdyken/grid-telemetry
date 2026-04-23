<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { getCircuitPath } from '~/lib/api'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  telemetry: CarDataRecord | null
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

  const padding = 1000
  const width = Math.max(1, maxX - minX + padding * 2)
  const height = Math.max(1, maxY - minY + padding * 2)

  return `${minX - padding} ${minY - padding} ${width} ${height}`
})

const circuitSvgPoints = computed(() => {
  return circuitPath.value.map(point => `${point.x},${point.y}`).join(' ')
})
</script>

<template>
  <div class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 shadow-lg flex flex-col min-h-[300px] relative">
    <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">TRACK MAP</h2>

    <svg :viewBox="viewBox" class="w-full h-full transform -scale-y-100 flex-1 mt-2">
      <polyline
        :points="circuitSvgPoints"
        fill="none"
        stroke="#333344"
        stroke-width="400"
        stroke-linejoin="round"
      />
      <circle
        v-if="props.telemetry?.x && props.telemetry?.y"
        :cx="props.telemetry.x"
        :cy="props.telemetry.y"
        r="500"
        fill="#00ff00"
        class="transition-all duration-200"
      />
    </svg>
  </div>
</template>
