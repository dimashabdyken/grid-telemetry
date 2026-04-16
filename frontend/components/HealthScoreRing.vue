<script setup lang="ts">
import { computed } from 'vue'

type Severity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'NORMAL'

const props = withDefaults(
  defineProps<{
    score: number
    severity?: Severity
  }>(),
  {
    severity: 'NORMAL'
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
</script>

<template>
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
</template>
