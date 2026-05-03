<script setup lang="ts">
import { computed } from 'vue'
import { TransitionPresets, useTransition } from '@vueuse/core'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  data: CarDataRecord | null
}>()

const throttle = computed(() => props.data?.throttle ?? 0)
const brake = computed(() => props.data?.brake ?? 0)
const rpm = computed(() => props.data?.rpm ?? 0)

const smoothRpm = useTransition(rpm, {
  duration: 150,
  transition: TransitionPresets.linear
})

const clampedThrottle = computed(() => Math.min(Math.max(throttle.value, 0), 100))
const clampedBrake = computed(() => Math.min(Math.max(brake.value, 0), 100))
const isDrsOpen = computed(() => [10, 12, 14].includes(props.data?.drs ?? 0))

const isLedActive = (i: number) => smoothRpm.value >= i * 1000

const ledColorClass = (i: number) => {
  if (i <= 5) {
    return 'text-[#00ff00]'
  }
  if (i <= 10) {
    return 'text-[#e10600]'
  }
  return 'text-[#005aff]'
}
</script>

<template>
  <div class="relative flex w-full flex-col gap-4 overflow-hidden border border-edge bg-surface p-5">
    <div class="relative flex items-center justify-between gap-2 border border-edge-dark bg-surface-elevated px-2 py-2">
      <div
        v-for="i in 15"
        :key="i"
        class="h-3 w-3 transition-all duration-100"
        :class="[
          isLedActive(i)
            ? [ledColorClass(i), 'bg-current shadow-[0_0_8px_currentColor]']
            : 'bg-gray-800'
        ]"
      />
    </div>

    <div class="grid grid-cols-3 gap-2 mb-4 items-center">
      <!-- Speed -->
      <div class="bg-surface-elevated border border-edge-dark p-2 flex flex-col items-center">
        <div class="text-3xl font-black text-white tracking-tighter font-mono">{{ Math.round(data?.speed ?? 0) }}</div>
        <div class="text-[8px] text-gray-500 uppercase tracking-widest font-mono">KM/H</div>
      </div>
      <!-- Gear -->
      <div class="bg-surface-elevated border border-edge-dark p-2 flex flex-col items-center">
        <div class="text-3xl font-black text-white font-mono">{{ data?.n_gear ?? 0 }}</div>
        <div class="text-[8px] text-gray-500 uppercase tracking-widest font-mono">GEAR</div>
      </div>
      <!-- DRS -->
      <div
        class="h-full flex items-center justify-center border text-[8px] font-mono uppercase tracking-widest transition-colors duration-200"
        :class="isDrsOpen ? 'bg-green-500/20 border-green-500 text-green-400' : 'bg-surface-elevated border-edge-dark text-gray-600'"
      >
        DRS
      </div>
    </div>

    <div class="relative w-full border border-edge-dark bg-surface-elevated p-4">
      <div class="relative mb-2 text-xs font-mono uppercase tracking-widest text-gray-400">
        THROTTLE
      </div>
      <div class="relative h-1 w-full overflow-hidden bg-edge-dark">
        <div
          class="h-full w-full bg-[#00ff00] origin-left transition-transform duration-100"
          :style="{ transform: `scaleX(${clampedThrottle / 100})` }"
        />
      </div>

      <div class="relative mt-4 mb-2 text-xs font-mono uppercase tracking-widest text-gray-400">
        BRAKE
      </div>
      <div class="relative h-1 w-full overflow-hidden bg-edge-dark">
        <div
          class="h-full w-full bg-[#e10600] origin-left transition-transform duration-100"
          :style="{ transform: `scaleX(${clampedBrake / 100})` }"
        />
      </div>

      <div class="relative mt-4 mb-1 text-xs font-mono uppercase tracking-widest text-gray-400">
        RPM
      </div>
      <div class="relative mt-2 h-1 w-full overflow-hidden bg-edge-dark">
        <div
          class="h-full w-full bg-[#005aff] origin-left transition-transform duration-100"
          :style="{ transform: `scaleX(${Math.min(smoothRpm / 15000, 1)})` }"
        />
      </div>
      <div class="text-right text-xs text-slate-400 tabular-nums mt-1 font-mono">
        {{ Math.round(smoothRpm) }}
      </div>
    </div>
  </div>
</template>
