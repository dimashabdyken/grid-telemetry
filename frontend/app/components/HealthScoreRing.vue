<script setup lang="ts">
import { computed } from 'vue'

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NORMAL'

type HealthSnapshot = {
  engine_load?: number
  brake_agg?: number
  brake_aggression?: number
  trans_stress?: number
}

type CurrentHealth = {
  snapshot?: HealthSnapshot
}

const props = withDefaults(
  defineProps<{
    score: number
    severity?: Severity
    currentHealth?: CurrentHealth | null
  }>(),
  {
    severity: 'NORMAL',
    currentHealth: null
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
  Math.min(100, Math.max(0, props.currentHealth?.snapshot?.engine_load ?? 0))
)

const normalizedBrakeAggression = computed(() =>
  Math.min(
    100,
    Math.max(
      0,
      props.currentHealth?.snapshot?.brake_agg ??
        props.currentHealth?.snapshot?.brake_aggression ??
        0
    )
  )
)

const normalizedTransStress = computed(() =>
  Math.min(100, Math.max(0, props.currentHealth?.snapshot?.trans_stress ?? 0))
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

const transStressTextClass = computed(() =>
  normalizedTransStress.value > 85 ? 'text-orange-400' : 'text-white'
)

const transStressBarClass = computed(() =>
  normalizedTransStress.value > 90 ? 'bg-red-500' : 'bg-blue-500'
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

    <div class="mt-1 grid w-full grid-cols-3 gap-2 text-center">
      <div class="flex flex-col items-center rounded-md border border-white/5 bg-black/20 px-2 py-2">
        <div class="text-[9px] font-bold uppercase tracking-widest text-gray-500">
          ENG
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
      <div class="flex flex-col items-center rounded-md border border-white/5 bg-black/20 px-2 py-2">
        <div class="text-[9px] font-bold uppercase tracking-widest text-gray-500">
          BRK
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
      <div class="flex flex-col items-center rounded-md border border-white/5 bg-black/20 px-2 py-2">
        <div class="text-[9px] font-bold uppercase tracking-widest text-gray-500">
          TRN
        </div>
        <div
          class="text-sm font-black tabular-nums transition-colors duration-300"
          :class="transStressTextClass"
        >
          {{ Math.round(normalizedTransStress) }}%
        </div>
        <div class="mt-1 h-1 w-full overflow-hidden rounded-full bg-gray-800">
          <div
            class="h-full transition-all duration-300"
            :class="transStressBarClass"
            :style="{ width: `${normalizedTransStress}%` }"
          />
        </div>
      </div>
    </div>
  </div>
</template>
