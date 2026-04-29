<script setup lang="ts">
const props = withDefaults(defineProps<{
  warnings?: string[]
}>(), {
  warnings: () => []
})

const WARNING_LABELS: Record<string, string> = {
  SUSTAINED_WOT: 'MAXIMUM THROTTLE DURATION EXCEEDED',
  RPM_REDLINE_BREACH: 'ENGINE RPM REDLINE BREACH',
  HEAVY_BRAKE_EVENT: 'EXCESSIVE BRAKE LOAD',
  STUCK_THROTTLE_STATIONARY: 'THROTTLE STUCK - STATIONARY',
  DRS_FAULT: 'DRS SYSTEM FAULT',
  POSSIBLE_MISSED_GEAR: 'GEAR SHIFT ERROR'
}
</script>

<template>
  <div
    v-if="props.warnings.length === 0"
    class="p-3 rounded-lg uppercase font-black tracking-widest text-sm flex items-center justify-center gap-4 transition-colors duration-300 bg-emerald-950/30 border border-[#00ff00]/30 text-[#00ff00]"
  >
    <span class="w-3 h-3 rounded-full bg-[#00ff00]" />
    ALL SYSTEMS NOMINAL
  </div>

  <div
    v-else
    class="p-3 rounded-lg uppercase font-black tracking-widest text-sm flex items-center justify-center gap-4 transition-colors duration-300 bg-red-950/80 border-2 border-[#e10600] text-white animate-pulse shadow-[0_0_15px_rgba(225,6,0,0.5)]"
  >
    <span class="w-3 h-3 rounded-full bg-[#e10600]" />
    MASTER WARNING: {{ props.warnings.map(warning => WARNING_LABELS[warning] || warning).join(' | ') }}
  </div>
</template>
