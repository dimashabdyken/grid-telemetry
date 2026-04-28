<script setup lang="ts">
import { computed } from 'vue'

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NORMAL'

const props = withDefaults(
  defineProps<{
    score: number
    severity?: Severity
    engineLoad?: number
    brakeAggression?: number
  }>(),
  {
    severity: 'NORMAL',
    engineLoad: 0,
    brakeAggression: 0
  }
)

const radius = 40
const circumference = 2 * Math.PI * radius

const normalizedScore = computed(() => Math.min(100, Math.max(0, props.score)))

const strokeDashoffset = computed(() =>
  circumference - (normalizedScore.value / 100) * circumference
)

const colorClass = computed(() => {
  if (props.severity === 'CRITICAL' || props.severity === 'HIGH') {
    return 'text-[#e10600]'
  }

  if (props.severity === 'LOW' || props.severity === 'MEDIUM') {
    return 'text-[#fff200]'
  }

  if (props.severity === 'NORMAL') {
    return 'text-[#00ff00]'
  }

  if (normalizedScore.value >= 80) {
    return 'text-[#00ff00]'
  }

  if (normalizedScore.value >= 50) {
    return 'text-[#fff200]'
  }

  return 'text-[#e10600]'
})

const pulseClass = computed(() =>
  props.severity === 'CRITICAL' ? 'animate-pulse' : ''
)

const normalizedEngineLoad = computed(() =>
  Math.min(100, Math.max(0, props.engineLoad))
)

const normalizedBrakeAggression = computed(() =>
  Math.min(100, Math.max(0, props.brakeAggression))
)

const engineLoadTextClass = computed(() =>
  normalizedEngineLoad.value > 85 ? 'text-orange-400' : 'text-white'
)

const engineLoadBarClass = computed(() =>
  normalizedEngineLoad.value > 90 ? 'bg-red-500' : 'bg-emerald-500'
)

const brakeAggressionTextClass = computed(() =>
  normalizedBrakeAggression.value > 85 ? 'text-orange-400' : 'text-white'
)

const brakeAggressionBarClass = computed(() =>
  normalizedBrakeAggression.value > 90 ? 'bg-red-500' : 'bg-emerald-500'
)
</script>

<template>
  <div class="flex flex-col items-center gap-3">
    <div
      class="relative flex items-center justify-center w-32 h-32"
      :class="pulseClass"
    >
      <svg class="w-full h-full -rotate-90" viewBox="0 0 100 100">
        <circle
          cx="50"
          cy="50"
          r="40"
          stroke="currentColor"
          stroke-width="8"
          fill="transparent"
          class="text-[#15151e]"
        />
        <circle
          cx="50"
          cy="50"
          r="40"
          stroke="currentColor"
          stroke-width="8"
          fill="transparent"
          stroke-linecap="round"
          :stroke-dasharray="circumference"
          :stroke-dashoffset="strokeDashoffset"
          :class="[colorClass, 'transition-all duration-500 ease-in-out']"
        />
      </svg>

      <div class="absolute inset-0 flex flex-col items-center justify-center">
        <div class="text-4xl font-black text-white tabular-nums tracking-tighter">
          {{ Math.round(normalizedScore) }}
        </div>
        <div class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-bold">
          HEALTH
        </div>
      </div>
    </div>

    <div class="grid w-full grid-cols-2 gap-2 text-center">
      <div class="rounded-md border border-white/5 bg-black/20 px-2 py-2">
        <div class="text-[9px] font-bold uppercase tracking-widest text-gray-500">
          Engine Load
        </div>
        <div
          class="text-sm font-black tabular-nums transition-colors duration-300"
          :class="engineLoadTextClass"
        >
          {{ Math.round(normalizedEngineLoad) }}%
        </div>
        <div class="mt-1 h-1 w-full overflow-hidden rounded-full bg-gray-800">
          <div
            class="h-full transition-all duration-300"
            :class="engineLoadBarClass"
            :style="{ width: `${normalizedEngineLoad}%` }"
          />
        </div>
      </div>
      <div class="rounded-md border border-white/5 bg-black/20 px-2 py-2">
        <div class="text-[9px] font-bold uppercase tracking-widest text-gray-500">
          Brake Agg.
        </div>
        <div
          class="text-sm font-black tabular-nums transition-colors duration-300"
          :class="brakeAggressionTextClass"
        >
          {{ Math.round(normalizedBrakeAggression) }}%
        </div>
        <div class="mt-1 h-1 w-full overflow-hidden rounded-full bg-gray-800">
          <div
            class="h-full transition-all duration-300"
            :class="brakeAggressionBarClass"
            :style="{ width: `${normalizedBrakeAggression}%` }"
          />
        </div>
      </div>
    </div>
  </div>
</template>
