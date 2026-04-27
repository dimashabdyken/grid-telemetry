<script setup lang="ts">
import { computed } from 'vue'
import { TransitionPresets, useTransition } from '@vueuse/core'
import type { CarDataRecord } from '~/lib/types'

const props = defineProps<{
  data: CarDataRecord | null
}>()

const speed = computed(() => props.data?.speed ?? 0)
const gear = computed(() => props.data?.n_gear ?? 0)
const throttle = computed(() => props.data?.throttle ?? 0)
const brake = computed(() => props.data?.brake ?? 0)
const rpm = computed(() => props.data?.rpm ?? 0)
// DRS is active if value is >= 8
const isDrsActive = computed(() => (props.data?.drs ?? 0) >= 8)

const smoothSpeed = useTransition(speed, {
  duration: 150,
  transition: TransitionPresets.linear
})
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

    <div class="grid grid-cols-2 gap-3 mb-2">
      <div class="bg-[#0a0a0f] rounded-lg border border-white/5 p-3 flex flex-col items-center justify-center shadow-inner">
        <div class="text-4xl xl:text-5xl font-black italic text-white tracking-tighter tabular-nums leading-none">
          {{ Math.round(smoothSpeed) }}
        </div>
        <div class="text-[10px] text-gray-500 uppercase tracking-[0.2em] mt-1 font-bold">
          KM/H
        </div>
      </div>

      <div class="bg-[#0a0a0f] rounded-lg border border-white/5 p-3 flex items-center justify-center gap-3 shadow-inner">
        <div class="flex flex-col items-center justify-center">
          <div class="text-4xl xl:text-5xl font-black italic text-white tracking-tighter tabular-nums leading-none">
            {{ gear }}
          </div>
          <div class="text-[10px] text-gray-500 uppercase tracking-[0.2em] mt-1 font-bold">
            GEAR
          </div>
        </div>
        <div
          class="px-2 py-1 rounded border text-[10px] font-black uppercase tracking-widest transition-all duration-100"
          :class="isDrsActive
            ? 'bg-green-500/20 border-green-500 text-green-400 shadow-[0_0_10px_#22c55e]'
            : 'bg-gray-800 border-gray-700 text-gray-600'"
        >
          {{ data ? 'DRS' : 'N/A' }}
        </div>
        <div class="text-[8px] text-gray-500">DRS_RAW: {{ data?.drs }}</div>
      </div>
    </div>

    <div class="relative rounded-xl border border-white/10 bg-black/50 p-4">
      <div class="pointer-events-none absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.06)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.05)_1px,transparent_1px)] bg-[size:14px_14px] opacity-20" />

      <div class="relative mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">
        THROTTLE
      </div>
      <div class="relative h-4 overflow-hidden rounded bg-white/10 -skew-x-12">
        <div
          class="h-full bg-[#00ff00] transition-all duration-100 shadow-[0_0_8px_rgba(0,255,0,0.75)]"
          :style="{ width: clampedThrottle + '%' }"
        />
      </div>

      <div class="relative mt-4 mb-2 text-xs font-bold uppercase tracking-widest text-gray-400">
        BRAKE
      </div>
      <div class="relative h-4 overflow-hidden rounded bg-white/10 -skew-x-12">
        <div
          class="h-full bg-[#e10600] transition-all duration-100 shadow-[0_0_8px_rgba(225,6,0,0.75)]"
          :style="{ width: clampedBrake + '%' }"
        />
      </div>

      <div class="relative mt-4 mb-1 text-xs font-bold uppercase tracking-widest text-gray-400">
        RPM
      </div>
      <div class="relative mt-2 h-2 overflow-hidden rounded bg-white/10">
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
