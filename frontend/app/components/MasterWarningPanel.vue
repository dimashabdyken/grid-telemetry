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
  POSSIBLE_MISSED_GEAR: 'GEAR SHIFT ERROR',
  THERMAL_WARNING: 'THERM-AI COCKPIT HEAT RISK',
  PCM_SATURATED: 'THERM-AI PCM SATURATION',
  COGNITIVE_DEGRADED: 'THERM-AI COGNITIVE LOAD DEGRADED',
  SEEBECK_ACTIVE: 'THERM-AI HEAT RECOVERY ACTIVE'
}
</script>

<template>
  <div
    v-if="props.warnings.length === 0"
    class="p-3 uppercase font-mono tracking-[0.2em] text-xs flex items-center justify-center gap-3 transition-colors duration-300 bg-emerald-950/20 border border-[#00ff00]/30 text-[#00ff00]"
  >
    <span class="w-2 h-2 bg-[#00ff00]" />
    ALL SYSTEMS NOMINAL
  </div>

  <div
    v-else
    class="p-3 uppercase font-mono tracking-[0.2em] text-xs flex items-center justify-center gap-3 transition-colors duration-300 bg-red-950/40 border border-[#e10600] text-white animate-pulse"
  >
    <span class="w-2 h-2 bg-[#e10600]" />
    MASTER WARNING: {{ props.warnings.map(warning => WARNING_LABELS[warning] || warning).join(' | ') }}
  </div>
</template>
