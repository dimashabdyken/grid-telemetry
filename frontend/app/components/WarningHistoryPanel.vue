<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { getWarningsHistory, type WarningEvent } from '~/lib/api'

const props = withDefaults(
  defineProps<{
    liveWarnings?: string[]
  }>(),
  {
    liveWarnings: () => []
  }
)

const events = ref<WarningEvent[]>([])
const loading = ref(true)
let refreshTimer: ReturnType<typeof setInterval> | null = null

const severityByCode: Record<string, string> = {
  NO_DATA: 'CRITICAL',
  RPM_REDLINE_BREACH: 'HIGH',
  STUCK_THROTTLE_STATIONARY: 'HIGH',
  HEAVY_BRAKE_EVENT: 'MEDIUM',
  DRS_FAULT: 'MEDIUM',
  SUSTAINED_WOT: 'LOW',
  POSSIBLE_MISSED_GEAR: 'LOW'
}

const formatTime = (value: string) => {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString()
}

const severityClass = (severity: string) => {
  if (severity === 'CRITICAL' || severity === 'HIGH') {
    return 'text-[#e10600]'
  }
  if (severity === 'MEDIUM') {
    return 'text-[#fff200]'
  }
  return 'text-gray-400'
}

const loadEvents = async () => {
  try {
    const data = await getWarningsHistory(9161, 20)
    events.value = Array.isArray(data) ? data : []
  } catch {
    events.value = []
  } finally {
    loading.value = false
  }
}

const displayedEvents = computed(() => {
  const liveEvents = props.liveWarnings.map((code) => ({
    code,
    severity: severityByCode[code] || 'LOW',
    triggered_at: 'LIVE'
  }))
  const liveCodes = new Set(liveEvents.map((event) => event.code))
  const historicalEvents = events.value.filter((event) => !liveCodes.has(event.code))

  return [...liveEvents, ...historicalEvents]
})

onMounted(async () => {
  await loadEvents()
  refreshTimer = setInterval(loadEvents, 5000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<template>
  <section class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 shadow-lg">
    <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold mb-4">
      EVENT LOG
    </h2>

    <div class="h-64 overflow-y-auto">
      <div v-if="loading" class="text-sm text-gray-500 py-2">
        Loading events...
      </div>

      <div v-else-if="displayedEvents.length === 0" class="text-sm text-gray-500 py-2">
        No warning events found.
      </div>

      <div
        v-for="(event, index) in displayedEvents"
        :key="`${event.code}-${event.triggered_at}-${index}`"
        class="border-b border-white/5 py-2"
      >
        <div class="flex items-center justify-between gap-3">
          <span class="text-white font-bold text-sm">{{ event.code }}</span>
          <span class="text-xs font-bold uppercase" :class="severityClass(event.severity)">
            {{ event.severity }}
          </span>
        </div>
        <div class="text-gray-500 text-xs mt-1">
          {{ formatTime(event.triggered_at) }}
        </div>
      </div>
    </div>
  </section>
</template>
