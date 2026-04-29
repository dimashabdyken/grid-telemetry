<script setup lang="ts">
import { computed } from 'vue'
import type { TyreStatus } from '~/lib/api'

const props = defineProps<{
  tyreStatus: TyreStatus | null
}>()

const compoundMap: Record<string, { color: string; maxLife: number; temp: string; deg: string }> = {
  SOFT: { color: '#e10600', maxLife: 25, temp: '105-125°C', deg: 'High' },
  MEDIUM: { color: '#fff200', maxLife: 40, temp: '110-130°C', deg: 'Linear' },
  HARD: { color: '#ffffff', maxLife: 60, temp: '115-135°C', deg: 'Low' },
  INTERMEDIATE: { color: '#00ff00', maxLife: 35, temp: '85-105°C', deg: 'Variable' },
  WET: { color: '#005aff', maxLife: 50, temp: '65-85°C', deg: 'Variable' },
}
const defaultTyre = { color: '#6b7280', maxLife: 30, temp: 'N/A', deg: 'N/A' }

const tyreData = computed(() =>
  compoundMap[props.tyreStatus?.compound?.toUpperCase() || 'UNKNOWN'] || defaultTyre
)

const gripLevel = computed(() => {
  if (!props.tyreStatus) return 0
  const wear = Math.min((props.tyreStatus.life / tyreData.value.maxLife) * 100, 100)
  return Math.max(100 - wear, 0)
})

const lapsRemaining = computed(() => {
  if (!props.tyreStatus) return 0
  return Math.max(0, tyreData.value.maxLife - props.tyreStatus.life)
})

const gripBarClass = computed(() => {
  if (gripLevel.value < 30) return 'bg-red-500'
  if (gripLevel.value < 60) return 'bg-amber-400'
  return 'bg-emerald-500'
})

const colorClass = computed(() => {
  const compound = props.tyreStatus?.compound?.toUpperCase()

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
  <section class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg h-full min-h-[320px] overflow-hidden">
    <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">
      Tyre Status
    </h2>

    <div class="flex flex-row items-center gap-6">
      <div
        class="w-16 h-16 rounded-full border-4 flex items-center justify-center font-black text-2xl"
        :class="colorClass"
      >
        {{ tyreStatus?.compound?.charAt(0) || '?' }}
      </div>

      <div class="flex flex-col gap-1">
        <p class="text-xl font-black text-white uppercase">
          {{ tyreStatus?.compound || 'Unknown' }}
        </p>
        <p class="text-sm font-bold text-gray-400">
          {{ tyreStatus?.life || 0 }} LAPS OLD
        </p>
      </div>
    </div>

    <div class="w-full h-px bg-white/10 my-2"></div>

    <div class="flex flex-col h-full min-h-0 flex-1 justify-between pt-2">
      <div class="flex flex-col gap-2">
        <div class="flex items-center justify-between">
          <p class="text-[10px] font-bold uppercase tracking-widest text-gray-500">
            Est. Grip
          </p>
          <p class="text-sm font-black tabular-nums text-white">
            {{ Math.round(gripLevel) }}%
          </p>
        </div>
        <div class="h-2 w-full overflow-hidden rounded-full bg-black/40">
          <div
            class="h-full transition-all duration-700"
            :class="gripBarClass"
            :style="{ width: `${gripLevel}%` }"
          />
        </div>
      </div>

      <!-- Compound Specs -->
      <div class="grid grid-cols-2 gap-4 flex-1 content-center">
        <div class="flex flex-col bg-black/20 p-2.5 rounded-lg border border-white/5 shadow-inner">
          <span class="text-[9px] text-gray-500 uppercase font-bold tracking-wider">Opt. Temp</span>
          <span class="text-sm font-black text-white mt-1">{{ tyreData.temp }}</span>
        </div>
        <div class="flex flex-col bg-black/20 p-2.5 rounded-lg border border-white/5 shadow-inner">
          <span class="text-[9px] text-gray-500 uppercase font-bold tracking-wider">Degradation</span>
          <span class="text-sm font-black text-white mt-1">{{ tyreData.deg }}</span>
        </div>
      </div>

      <!-- Pit Window Predictor -->
      <div
        class="flex items-center justify-center p-3 rounded-lg border transition-all duration-300"
        :class="lapsRemaining <= 5 ? 'bg-red-500/20 border-red-500 animate-pulse' : 'bg-gray-800/30 border-white/5'"
      >
        <span
          class="font-black tracking-widest uppercase"
          :class="lapsRemaining <= 5 ? 'text-red-500 text-lg shadow-red-500 drop-shadow-md' : 'text-gray-400 text-xs'"
        >
          {{ lapsRemaining <= 5 ? 'BOX BOX BOX' : `PIT WINDOW IN ${lapsRemaining} LAPS` }}
        </span>
      </div>
    </div>
  </section>
</template>
