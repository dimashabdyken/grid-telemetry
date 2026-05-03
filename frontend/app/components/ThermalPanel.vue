<script setup lang="ts">
import { computed, toRef } from 'vue'
import { useThermalState } from '~/composables/useThermalState'
import type { ThermalState } from '~/lib/types'

const props = defineProps<{
  thermalData: ThermalState | null
}>()

const thermalRef = toRef(props, 'thermalData')

const {
  cockpitTempDisplay,
  pcmPercent,
  seebeckDisplay,
  cognitivePercent,
  alertLevel,
  alertColor,
  riskForecastDisplay,
  pcmForecastDisplay,
  driverCauseDisplay
} = useThermalState(thermalRef)

const seebeckPercent = computed(() => {
  const seebeckWatts = props.thermalData?.seebeck_watts ?? 0
  return Math.max(0, Math.min(100, (seebeckWatts / 10000) * 100))
})

const showAlert = computed(() => alertLevel.value !== 'none')

const alertBannerClass = computed(() => {
  if (alertLevel.value === 'critical') {
    return 'border-red-500/60 bg-red-500/15 text-red-300 animate-pulse'
  }

  if (alertLevel.value === 'warning') {
    return 'border-yellow-400/50 bg-yellow-400/15 text-yellow-300'
  }

  return 'hidden'
})

const alertText = computed(() =>
  props.thermalData?.auto_mode
    ? 'THERMAL CRITICAL — AUTO MODE ON'
    : 'THERMAL WARNING'
)

const metrics = computed(() => [
  {
    label: 'PCM Load',
    valueText: `${Math.round(pcmPercent.value)}%`,
    value: pcmPercent.value,
    barClass: 'bg-[#ff6b5f] shadow-[0_0_8px_rgba(255,107,95,0.75)]'
  },
  {
    label: 'Seebeck',
    valueText: seebeckDisplay.value,
    value: seebeckPercent.value,
    barClass: 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.65)]'
  },
  {
    label: 'Cognitive Resource',
    valueText: `${Math.round(cognitivePercent.value)}%`,
    value: cognitivePercent.value,
    barClass: 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.65)]'
  }
])
</script>

<template>
  <div class="relative flex w-full flex-col gap-4 overflow-hidden border border-edge bg-surface p-5">

    <div
      v-if="showAlert"
      class="relative border px-3 py-2 text-center text-[10px] font-mono uppercase tracking-[0.2em]"
      :class="alertBannerClass"
    >
      {{ alertText }}
    </div>

    <div class="relative flex items-start justify-between gap-3 border-b border-edge-dark pb-3">
      <div>
        <div class="flex flex-wrap items-center gap-2">
          <div class="text-[10px] font-mono uppercase tracking-[0.2em] text-gray-400">
            Thermal State
          </div>
          <div class="border border-purple-400/40 bg-purple-400/10 px-2 py-0.5 text-[9px] font-mono uppercase tracking-[0.2em] text-purple-300">
            THERM-AI
          </div>
        </div>
        <div class="mt-1 text-[10px] font-mono uppercase tracking-[0.2em] text-gray-600">
          Predictive Thermal Model
        </div>
        <div
          v-if="thermalData?.auto_mode"
          class="mt-2 inline-flex border border-red-500/50 bg-red-500/10 px-2 py-1 text-[9px] font-mono uppercase tracking-[0.2em] text-red-300"
        >
          Auto Cooling Mode
        </div>
      </div>

      <div
        v-if="thermalData"
        class="text-right text-3xl font-black tracking-tighter text-white tabular-nums font-mono"
        :class="alertColor"
      >
        {{ cockpitTempDisplay }}
      </div>
      <div
        v-else
        class="h-9 w-24 animate-pulse bg-white/10"
        aria-hidden="true"
      />
    </div>

    <div
      v-if="!thermalData"
      class="relative space-y-5"
      aria-label="Loading thermal telemetry"
    >
      <div
        v-for="label in ['PCM Load', 'Seebeck', 'Cognitive Resource']"
        :key="label"
      >
        <div class="mb-2 flex items-center justify-between">
          <div class="text-xs font-mono uppercase tracking-widest text-gray-500">
            {{ label }}
          </div>
          <div class="h-4 w-12 animate-pulse bg-white/10" />
        </div>
        <div class="h-1 w-full overflow-hidden bg-white/10">
          <div class="h-full w-1/3 animate-pulse bg-white/10" />
        </div>
      </div>
    </div>

    <div v-else class="relative space-y-4">
      <div class="border border-edge-dark bg-surface-elevated px-3 py-2">
        <div class="text-[9px] font-mono uppercase tracking-[0.2em] text-gray-500">
          Forecast Window
        </div>
        <div class="mt-1 text-xs font-mono uppercase tracking-widest text-white">
          {{ riskForecastDisplay }}
        </div>
        <div class="mt-1 text-[10px] font-mono uppercase tracking-wider text-gray-500">
          {{ pcmForecastDisplay }}
        </div>
        <div class="mt-2 text-[10px] font-mono uppercase tracking-wider text-purple-300">
          {{ driverCauseDisplay }}
        </div>
      </div>

      <div
        v-for="metric in metrics"
        :key="metric.label"
      >
        <div class="mb-2 flex items-center justify-between gap-3">
          <div class="min-w-0 text-xs font-mono uppercase tracking-widest text-gray-400">
            {{ metric.label }}
          </div>
          <div class="shrink-0 text-sm font-black tabular-nums text-white font-mono">
            {{ metric.valueText }}
          </div>
        </div>
        <div class="h-1 w-full overflow-hidden bg-edge-dark">
          <div
            class="h-full transition-all duration-300"
            :class="metric.barClass"
            :style="{ width: `${metric.value}%` }"
          />
        </div>
      </div>
    </div>
  </div>
</template>
