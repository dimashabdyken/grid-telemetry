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

const mapBounds = computed(() => {
  if (!circuitPath.value.length) {
    return {
      minX: -1000,
      minY: -1000,
      width: 2000,
      height: 2000
    }
  }

  const xs = circuitPath.value.map(point => point.x)
  const ys = circuitPath.value.map(point => point.y)

  const minX = Math.min(...xs)
  const maxX = Math.max(...xs)
  const minY = Math.min(...ys)
  const maxY = Math.max(...ys)

  const padding = Math.max((maxX - minX) * 0.05, (maxY - minY) * 0.05, 80)
  const width = Math.max(1, maxX - minX + padding * 2)
  const height = Math.max(1, maxY - minY + padding * 2)

  return {
    minX: minX - padding,
    minY: minY - padding,
    width,
    height
  }
})

const viewBox = computed(() => {
  const bounds = mapBounds.value
  return `${bounds.minX} ${bounds.minY} ${bounds.width} ${bounds.height}`
})

const circuitSvgPoints = computed(() => {
  return circuitPath.value.map(point => `${point.x},${point.y}`).join(' ')
})

const hasTelemetryPosition = computed(() => (
  props.telemetry?.x !== undefined
  && props.telemetry?.x !== null
  && props.telemetry?.y !== undefined
  && props.telemetry?.y !== null
))

const fallbackTelemetryPoint = computed(() => {
  if (!circuitPath.value.length) {
    return null
  }

  const rawTick = Number(props.telemetry?._id ?? 0)
  const tick = Number.isFinite(rawTick) ? Math.abs(Math.trunc(rawTick)) : 0
  const index = tick % circuitPath.value.length
  return circuitPath.value[index]
})

const carPoint = computed(() => {
  if (hasTelemetryPosition.value) {
    return {
      x: Number(props.telemetry!.x),
      y: Number(props.telemetry!.y)
    }
  }
  return fallbackTelemetryPoint.value
})

const trackStrokeWidth = computed(() => {
  const scale = Math.min(mapBounds.value.width, mapBounds.value.height)
  const dynamicWidth = scale * 0.02
  return Math.max(220, Math.min(800, dynamicWidth))
})

const carRadius = computed(() => {
  return Math.max(300, trackStrokeWidth.value * 1.2)
})

const carColor = computed(() => {
  return props.teamColor ? `#${props.teamColor}` : '#ffffff'
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
      <polyline
        :points="circuitSvgPoints"
        fill="none"
        stroke="#ffffff"
        stroke-opacity="0.15"
        :stroke-width="trackStrokeWidth"
        stroke-linejoin="round"
        stroke-linecap="round"
      />
      <g v-if="hasTelemetryPosition" class="transition-all duration-75">
        <circle
          :cx="props.telemetry!.x"
          :cy="props.telemetry!.y"
          r="1500"
          :fill="carColor"
          class="animate-ping opacity-75"
        />
        <circle
          :cx="props.telemetry!.x"
          :cy="props.telemetry!.y"
          r="800"
          :fill="carColor"
        />
      </g>
      <circle
        v-else-if="carPoint"
        :cx="carPoint.x"
        :cy="carPoint.y"
        :r="carRadius"
        :fill="carColor"
      />
    </svg>
  </div>
</template>
