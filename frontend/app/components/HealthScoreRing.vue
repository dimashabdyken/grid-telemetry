<script setup lang="ts">
import { computed } from 'vue'

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NORMAL'

type HealthSnapshot = {
  engine_load?: number
  brake_agg?: number
  brake_aggression?: number
  trans_stress?: number
  lap?: number
  lap_time?: string
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

const metrics = computed(() => [
  {
    label: 'ENG',
    value: normalizedEngineLoad.value,
    textClass: engineLoadTextClass.value,
    barClass: engineLoadBarClass.value
  },
  {
    label: 'BRK',
    value: normalizedBrakeAggression.value,
    textClass: brakeAggressionTextClass.value,
    barClass: brakeAggressionBarClass.value
  },
  {
    label: 'TRN',
    value: normalizedTransStress.value,
    textClass: transStressTextClass.value,
    barClass: transStressBarClass.value
  }
])
</script>

<template>
  <div class="flex h-full min-h-[220px] w-full flex-col gap-4">
    <div class="flex min-h-0 flex-1 flex-col items-center justify-center border-b border-edge-dark pb-4">
      <div
        class="relative flex h-32 w-32 shrink-0 items-center justify-center"
        :class="pulseClass"
      >
        <svg class="h-full w-full -rotate-90" viewBox="0 0 100 100">
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
          <div class="text-4xl font-black text-white tabular-nums tracking-tighter font-mono">
            {{ Math.round(normalizedScore) }}
          </div>
          <div class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono">
            HEALTH
          </div>
        </div>
      </div>
    </div>

    <div class="grid w-full shrink-0 grid-cols-3 gap-px border border-edge bg-edge text-center">
      <div
        v-for="metric in metrics"
        :key="metric.label"
        class="flex min-w-0 flex-col items-center justify-start bg-surface p-2"
      >
        <span class="text-[9px] font-mono uppercase tracking-wider text-gray-500">
          {{ metric.label }}
        </span>
        <span
          class="text-sm font-black tabular-nums leading-5 transition-colors duration-300 font-mono"
          :class="metric.textClass"
        >
          {{ Math.round(metric.value) }}%
        </span>
        <div class="mt-1 h-1 w-full overflow-hidden bg-edge-dark">
          <div
            class="h-full transition-all duration-300"
            :class="metric.barClass"
            :style="{ width: `${metric.value}%` }"
          />
        </div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4 border-t border-edge-dark pt-3 text-center">
      <div>
        <p class="text-[9px] font-mono uppercase tracking-wider text-gray-500">
          Current Lap
        </p>
        <p class="mt-1 text-sm font-black text-white font-mono">
          {{ currentHealth?.snapshot?.lap ?? '-' }}
        </p>
      </div>
      <div>
        <p class="text-[9px] font-mono uppercase tracking-wider text-gray-500">
          Last Lap Time
        </p>
        <p class="mt-1 text-sm font-black tabular-nums text-white font-mono">
          {{ currentHealth?.snapshot?.lap_time ?? '0:00.000' }}
        </p>
      </div>
    </div>
  </div>
</template>
