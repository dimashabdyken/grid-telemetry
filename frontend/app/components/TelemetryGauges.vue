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
  <div class="relative flex w-full flex-col gap-4 overflow-hidden rounded-2xl border border-white/10 bg-[#0a0a0f] p-4 shadow-[0_20px_40px_rgba(0,0,0,0.45)]">
    <div class="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(225,6,0,0.14),transparent_55%)]" />

    <div class="relative flex items-center justify-between gap-2 rounded-lg bg-black/70 px-2 py-3">
      <div
        v-for="i in 15"
        :key="i"
        class="h-3 w-3 rounded-full transition-all duration-100"
        :class="[
          isLedActive(i)
            ? [ledColorClass(i), 'bg-current shadow-[0_0_8px_currentColor]']
            : 'bg-gray-800'
        ]"
      />
    </div>

    <div class="grid grid-cols-3 gap-2 mb-4 items-center">
      <!-- Speed -->
      <div class="bg-[#0a0a0f] rounded-lg border border-white/5 p-2 flex flex-col items-center">
        <div class="text-3xl font-black italic text-white tracking-tighter">{{ Math.round(data?.speed ?? 0) }}</div>
        <div class="text-[8px] text-gray-500 uppercase tracking-widest">KM/H</div>
      </div>
      <!-- Gear -->
      <div class="bg-[#0a0a0f] rounded-lg border border-white/5 p-2 flex flex-col items-center">
        <div class="text-3xl font-black italic text-white">{{ data?.n_gear ?? 0 }}</div>
        <div class="text-[8px] text-gray-500 uppercase tracking-widest">GEAR</div>
      </div>
      <!-- DRS -->
      <div
        class="h-full flex items-center justify-center rounded border text-[8px] font-black uppercase tracking-widest transition-colors duration-200"
        :class="(data?.drs !== 0 && data?.drs != null) ? 'bg-green-500/20 border-green-500 text-green-400' : 'bg-gray-800 border-gray-700 text-gray-600'"
      >
        DRS
      </div>
    </div>

    <div class="relative w-full rounded-xl border border-white/10 bg-black/50 p-4">
      <div class="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:14px_14px] opacity-20" />

      <div class="relative mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">
        THROTTLE
      </div>
      <div class="relative h-4 w-full overflow-hidden rounded bg-white/10 -skew-x-12">
        <div
          class="h-full bg-[#00ff00] transition-all duration-100 shadow-[0_0_8px_rgba(0,255,0,0.75)]"
          :style="{ width: clampedThrottle + '%' }"
        />
      </div>

      <div class="relative mt-4 mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">
        BRAKE
      </div>
      <div class="relative h-4 w-full overflow-hidden rounded bg-white/10 -skew-x-12">
        <div
          class="h-full bg-[#e10600] transition-all duration-100 shadow-[0_0_8px_rgba(225,6,0,0.75)]"
          :style="{ width: clampedBrake + '%' }"
        />
      </div>

      <div class="relative mt-4 mb-1 text-xs font-bold uppercase tracking-widest text-gray-400">
        RPM
      </div>
      <div class="relative mt-2 h-2 w-full overflow-hidden rounded bg-white/10">
        <div
          class="h-full bg-[#005aff] transition-all duration-100"
          :style="{ width: Math.min((smoothRpm / 15000) * 100, 100) + '%' }"
        />
      </div>
      <div class="text-right text-xs text-slate-400 tabular-nums mt-1 font-bold">
        {{ Math.round(smoothRpm) }}
      </div>
    </div>
  </div>
</template>
