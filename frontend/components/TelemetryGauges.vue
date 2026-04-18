<script setup lang="ts">
import { computed } from 'vue'
import type { CarDataRecord } from '~~/lib/types'

const props = defineProps<{
  data: CarDataRecord | null
}>()

const speed = computed(() => props.data?.speed ?? 0)
const gear = computed(() => props.data?.n_gear ?? 0)
const throttle = computed(() => props.data?.throttle ?? 0)
const brake = computed(() => props.data?.brake ?? 0)
const rpm = computed(() => props.data?.rpm ?? 0)
</script>

<template>
  <div class="flex w-full flex-col gap-4">
    <div class="grid grid-cols-2 gap-4">
      <div class="rounded bg-black/60 p-4">
        <div class="text-5xl font-black tabular-nums text-white">
          {{ speed }}
        </div>
        <div class="text-xs uppercase tracking-widest text-gray-500">
          KM/H
        </div>
      </div>

      <div class="rounded bg-black/60 p-4">
        <div class="text-5xl font-black tabular-nums text-white">
          {{ gear }}
        </div>
        <div class="text-xs uppercase tracking-widest text-gray-500">
          GEAR
        </div>
      </div>
    </div>

    <div class="rounded bg-black/60 p-4">
      <div class="mb-1 text-xs font-bold uppercase tracking-widest text-gray-400">
        THROTTLE
      </div>
      <div class="h-3 overflow-hidden rounded bg-white/10">
        <div
          class="h-full bg-[#00ff00] transition-all duration-75"
          :style="{ width: Math.min(Math.max(throttle, 0), 100) + '%' }"
        />
      </div>

      <div class="mt-3 mb-1 text-xs font-bold uppercase tracking-widest text-gray-400">
        BRAKE
      </div>
      <div class="h-3 overflow-hidden rounded bg-white/10">
        <div
          class="h-full bg-[#e10600] transition-all duration-75"
          :style="{ width: Math.min(Math.max(brake, 0), 100) + '%' }"
        />
      </div>

      <div class="mt-3 mb-1 text-xs font-bold uppercase tracking-widest text-gray-400">
        RPM
      </div>
      <div class="mt-2 h-2 overflow-hidden rounded bg-white/10">
        <div
          class="h-full bg-blue-500 transition-all duration-75"
          :style="{ width: Math.min((rpm / 15000) * 100, 100) + '%' }"
        />
      </div>
    </div>
  </div>
</template>