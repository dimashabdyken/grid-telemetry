<script setup lang="ts">
import { computed } from 'vue'
import type { F1Driver } from '~/lib/types'

const props = defineProps<{
  driver: F1Driver | null
  livePosition?: number | string
  liveGap?: string
  livePitStops?: number | string
}>()

const positionLabel = computed(() =>
  props.livePosition ?? props.driver?.position ?? '-'
)

const pitStopsLabel = computed(() => props.livePitStops ?? 0)
</script>

<template>
  <div class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg relative overflow-hidden h-full">
    <div
      class="absolute top-0 left-0 w-1 h-full"
      :style="{ backgroundColor: '#' + (driver?.team_colour || 'ffffff') }"
    />

    <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">
      Driver Identity
    </h2>

    <div class="flex flex-row items-center gap-4">
      <img
        v-if="driver?.headshot_url"
        :src="driver.headshot_url"
        class="w-16 h-16 rounded-full object-cover border-2 border-white/10"
      />
      <div
        v-else
        class="w-16 h-16 rounded-full border-2 border-white/10 bg-black/40 text-white font-black text-lg flex items-center justify-center"
      >
        {{ driver?.name_acronym || driver?.abbreviation || '---' }}
      </div>

      <div class="min-w-0 flex flex-col justify-center gap-1">
        <p class="text-xl md:text-2xl font-black text-white uppercase tracking-tighter leading-none break-words whitespace-normal">
          {{ driver?.full_name || driver?.name || 'Loading...' }}
        </p>
        <p class="text-sm font-bold text-gray-400">
          {{ driver?.team_name || 'N/A' }} | #{{ driver?.driver_number || '?' }}
        </p>
      </div>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-4 text-center">
      <div class="rounded bg-black/20 p-2">
        <p class="text-[9px] font-bold uppercase text-gray-500">Position</p>
        <p class="text-lg font-black text-white">P{{ positionLabel }}</p>
      </div>
      <div class="rounded bg-black/20 p-2">
        <p class="text-[9px] font-bold uppercase text-gray-500">Gap</p>
        <p class="text-lg font-black text-white">
          {{ liveGap ?? driver?.gap ?? 'N/A' }}
        </p>
      </div>
    </div>

    <div class="mt-6 grid grid-cols-2 gap-4 border-t border-white/10 pt-4">
      <div class="flex flex-col items-center">
        <span class="text-[9px] font-bold uppercase tracking-widest text-gray-500">
          Pit Stops
        </span>
        <span class="text-xl font-black text-white">{{ pitStopsLabel }}</span>
      </div>
      <div class="flex flex-col items-center">
        <span class="text-[9px] font-bold uppercase tracking-widest text-gray-500">
          Track Status
        </span>
        <span class="mt-1 text-[10px] font-bold uppercase text-[#00ff00]">
          Track Clear
        </span>
      </div>
    </div>

    <div class="mt-4 flex items-center justify-between rounded-lg bg-white/5 p-3">
      <span class="text-[10px] uppercase text-gray-400">Race Condition</span>
      <span class="text-xs font-bold text-white">Dry</span>
    </div>
  </div>
</template>
