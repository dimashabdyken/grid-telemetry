<script setup lang="ts">
import { computed } from 'vue'
import type { TyreStatus } from '~/lib/api'

const props = defineProps<{
  tyreStatus: TyreStatus | null
}>()

const colorClass = computed(() => {
  const compound = props.tyreStatus?.compound?.toUpperCase()

  switch (compound) {
    case 'SOFT':
      return 'text-[#e10600] border-[#e10600]'
    case 'MEDIUM':
      return 'text-[#fff200] border-[#fff200]'
    case 'HARD':
      return 'text-white border-white'
    case 'INTERMEDIATE':
      return 'text-[#00ff00] border-[#00ff00]'
    case 'WET':
      return 'text-[#005aff] border-[#005aff]'
    default:
      return 'text-gray-500 border-gray-500'
  }
})
</script>

<template>
  <section class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg h-full">
    <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">
      Tyre Status
    </h2>

    <div class="flex flex-row items-center gap-6">
      <div
        class="w-16 h-16 rounded-full border-4 flex items-center justify-center font-black text-2xl"
        :class="colorClass"
      >
        {{ tyreStatus?.compound.charAt(0) || '?' }}
      </div>

      <div class="flex flex-col gap-1">
        <p class="text-xl font-black text-white uppercase">
          {{ tyreStatus?.compound || 'Unknown' }}
        </p>
        <p class="text-sm font-bold text-gray-400">
          {{ tyreStatus?.life || 0 }} LAPS OLD
        </p>
      </div>
    </div>
  </section>
</template>
