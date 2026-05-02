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
  <div class="bg-[#0f0f13] p-5 border border-[#333] flex flex-col gap-4 relative overflow-hidden h-full shadow-none rounded-none">
    <div
      class="absolute top-0 left-0 w-2 h-full"
      :style="{ backgroundColor: '#' + (driver?.team_colour || 'ffffff') }"
    />

    <h2 class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono border-b border-[#222] pb-2">
      Driver Identity
    </h2>

    <div class="flex flex-row items-center gap-4">
      <img
        v-if="driver?.headshot_url"
        :src="driver.headshot_url"
        class="w-16 h-16 rounded-none object-cover border border-[#444] mix-blend-luminosity opacity-90"
      />
      <div
        v-else
        class="w-16 h-16 border border-[#333] bg-black text-white font-mono text-xl flex items-center justify-center"
      >
        {{ driver?.name_acronym || driver?.abbreviation || '---' }}
      </div>

      <div class="min-w-0 flex flex-col justify-center gap-1">
        <p class="text-2xl font-black text-white uppercase tracking-tight leading-none break-words whitespace-normal">
          {{ driver?.full_name || driver?.name || 'Loading...' }}
        </p>
        <p class="text-xs font-mono text-gray-400">
          {{ driver?.team_name || 'N/A' }} | #{{ driver?.driver_number || '?' }}
        </p>
      </div>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-px bg-[#333] border border-[#333]">
      <div class="bg-[#0f0f13] p-3 text-center">
        <p class="text-[10px] font-mono uppercase tracking-widest text-gray-400 mb-1">Position</p>
        <p class="text-2xl font-black font-mono text-white">P{{ positionLabel }}</p>
      </div>
      <div class="bg-[#0f0f13] p-3 text-center">
        <p class="text-[10px] font-mono uppercase tracking-widest text-gray-400 mb-1">Gap</p>
        <p class="text-2xl font-black font-mono text-white">
          {{ liveGap ?? driver?.gap ?? 'N/A' }}
        </p>
      </div>
    </div>

    <div class="mt-4 grid grid-cols-2 gap-px bg-[#333] border border-[#333]">
      <div class="flex flex-col items-center bg-[#0f0f13] p-3">
        <span class="text-[10px] font-mono uppercase tracking-widest text-gray-400 mb-1">
          Pit Stops
        </span>
        <span class="text-xl font-black font-mono text-white">{{ pitStopsLabel }}</span>
      </div>
      <div class="flex flex-col items-center bg-[#0f0f13] p-3">
        <span class="text-[10px] font-mono uppercase tracking-widest text-gray-400 mb-1">
          Track Status
        </span>
        <span class="mt-2 text-[10px] font-mono uppercase tracking-wider text-[#00ff00] bg-[#00ff00]/10 px-2 py-1 border border-[#00ff00]/30 outline outline-1 outline-offset-2 outline-transparent">
          TRACK CLEAR
        </span>
      </div>
    </div>

    <div class="mt-4 flex items-center justify-between border-t border-[#222] pt-3">
      <span class="text-[10px] font-mono uppercase tracking-widest text-gray-400">Race Condition</span>
      <span class="text-xs font-mono font-bold text-white bg-white/10 px-2 py-1">DRY</span>
    </div>
  </div>
</template>
