<script setup lang="ts">
import { computed } from 'vue'
import type { TyreStatus } from '~/lib/api'

const props = defineProps<{
  tyreStatus?: TyreStatus | null
  liveCompound?: string
  liveLife?: number
}>()

const compoundMap: Record<string, { color: string; maxLife: number; temp: string; deg: string }> = {
  SOFT: { color: '#e10600', maxLife: 25, temp: '105-125°C', deg: 'High' },
  MEDIUM: { color: '#fff200', maxLife: 40, temp: '110-130°C', deg: 'Linear' },
  HARD: { color: '#ffffff', maxLife: 60, temp: '115-135°C', deg: 'Low' },
  INTERMEDIATE: { color: '#00ff00', maxLife: 35, temp: '85-105°C', deg: 'Variable' },
  WET: { color: '#005aff', maxLife: 50, temp: '65-85°C', deg: 'Variable' },
}
const defaultTyre = { color: '#6b7280', maxLife: 30, temp: 'N/A', deg: 'N/A' }

const activeCompound = computed(() =>
  props.liveCompound || props.tyreStatus?.compound || 'UNKNOWN'
)

const activeLife = computed(() =>
  props.liveLife ?? props.tyreStatus?.life ?? 0
)

const tyreData = computed(() =>
  compoundMap[activeCompound.value.toUpperCase()] || defaultTyre
)

const gripLevel = computed(() => {
  const wear = Math.min((activeLife.value / tyreData.value.maxLife) * 100, 100)
  return Math.max(100 - wear, 0)
})

const lapsRemaining = computed(() => {
  return Math.max(0, tyreData.value.maxLife - activeLife.value)
})

const gripBarClass = computed(() => {
  if (gripLevel.value < 30) return 'bg-red-500'
  if (gripLevel.value < 60) return 'bg-amber-400'
  return 'bg-emerald-500'
})

const colorClass = computed(() => {
  const compound = activeCompound.value.toUpperCase()

  switch (compound) {
    case 'SOFT':
      return 'text-[#e10600] border-[#e10600]'
    case 'MEDIUM':
      return 'text-[#fff200] border-[#fff200]'
    case 'HARD':
      return 'text-white border-white'
    case 'INTERMEDIATE':
      return 'text-[#00ff00] border-[#00ff00]'
    case 'WET':
      return 'text-[#005aff] border-[#005aff]'
    default:
      return 'text-gray-500 border-gray-500'
  }
})
</script>

<template>
  <section class="bg-surface p-5 border border-edge flex flex-col gap-4 relative overflow-hidden h-full shadow-none rounded-none min-h-[320px]">
    <h2 class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono border-b border-edge-dark pb-2">
      Tyre Status
    </h2>

    <div class="flex flex-row items-center gap-6 mt-2">
      <div
        class="w-16 h-16 rounded-none border-2 flex items-center justify-center font-mono font-black text-2xl mix-blend-screen"
        :class="colorClass"
      >
        {{ activeCompound.charAt(0) || '?' }}
      </div>

      <div class="flex flex-col gap-1">
        <p class="text-2xl font-black font-mono text-white uppercase tracking-tight">
          {{ activeCompound }}
        </p>
        <p class="text-xs font-mono text-gray-400 uppercase tracking-widest">
          Laps: {{ activeLife }}
        </p>
      </div>
    </div>

    <div class="flex flex-col h-full min-h-0 flex-1 justify-between pt-2">
      <div class="flex flex-col gap-2 bg-surface-elevated p-3 border border-edge">
        <div class="flex items-center justify-between">
          <p class="text-[10px] font-mono uppercase tracking-widest text-gray-400">
            Est. Grip
          </p>
          <p class="text-sm font-mono font-black text-white">
            {{ Math.round(gripLevel) }}%
          </p>
        </div>
        <div class="h-1 w-full bg-black relative top-0 left-0 overflow-hidden">
          <div
            class="absolute top-0 left-0 h-full transition-transform duration-700 origin-left ease-out"
            :class="gripBarClass"
            :style="{ transform: `scaleX(${gripLevel / 100})` }"
          />
        </div>
      </div>

      <!-- Compound Specs -->
      <div class="grid grid-cols-2 gap-px bg-edge border border-edge mt-4">
        <div class="flex flex-col bg-surface p-3 text-center">
          <span class="text-[10px] text-gray-500 uppercase font-mono tracking-widest mb-1">Opt. Temp</span>
          <span class="text-lg font-black font-mono text-white mt-1">{{ tyreData.temp }}</span>
        </div>
        <div class="flex flex-col bg-surface p-3 text-center">
          <span class="text-[10px] text-gray-500 uppercase font-mono tracking-widest mb-1">Degradation</span>
          <span class="text-lg font-black font-mono text-white mt-1">{{ tyreData.deg }}</span>
        </div>
      </div>

      <!-- Pit Window Predictor -->
      <div
        class="mt-4 flex items-center justify-center p-3 border-t border-edge-dark"
        :class="lapsRemaining <= 5 ? 'bg-red-500/10 border-red-500' : 'bg-transparent border-edge-dark'"
      >
        <span
          class="font-mono font-bold tracking-[0.2em] uppercase"
          :class="lapsRemaining <= 5 ? 'text-red-500 text-sm animate-pulse flex items-center gap-2 before:content-[\'\'] before:w-2 before:h-2 before:bg-red-500' : 'text-gray-500 text-[10px]'"
        >
          {{ lapsRemaining <= 5 ? 'BOX BOX BOX' : `PIT WINDOW: ${lapsRemaining} LAPS` }}
        </span>
      </div>
    </div>
  </section>
</template>
