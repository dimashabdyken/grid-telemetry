<script setup lang="ts">
import type { F1Driver } from '~/lib/types'

defineProps<{
  driver: F1Driver | null
}>()
</script>

<template>
  <div class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg relative overflow-hidden">
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
  </div>
</template>