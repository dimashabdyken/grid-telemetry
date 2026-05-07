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

const warningCodeClass = (code: string) => {
  if (
    code.startsWith('THERMAL_') ||
    code.startsWith('PCM_') ||
    code.startsWith('COGNITIVE_') ||
    code.startsWith('SEEBECK_')
  ) {
    return 'text-purple-400'
  }

  return 'text-white'
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

  return [...liveEvents, ...historicalEvents].map((event) => ({
    ...event,
    key: event.triggered_at === 'LIVE'
      ? `live-${event.code}`
      : `${event.code}-${event.triggered_at}`
  }))
})

const expandedKey = ref<string | null>(null)

const toggleDetails = (key: string) => {
  expandedKey.value = expandedKey.value === key ? null : key
}

const isLiveEvent = (triggeredAt: string) => triggeredAt === 'LIVE'

const eventCategory = (code: string) => {
  if (code.startsWith('THERMAL_')) return 'THERMAL'
  if (code.startsWith('PCM_')) return 'PCM'
  if (code.startsWith('COGNITIVE_')) return 'COGNITIVE'
  if (code.startsWith('SEEBECK_')) return 'SEEBECK'
  return 'GENERAL'
}

const eventDomId = (key: string) => `event-details-${key.replace(/[^a-zA-Z0-9_-]/g, '')}`

onMounted(async () => {
  await loadEvents()
  refreshTimer = setInterval(loadEvents, 15000)
})

onUnmounted(() => {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<template>
  <section class="bg-surface border border-edge p-5">
    <div class="flex items-center justify-between border-b border-edge-dark pb-2">
      <h2 class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono">
        Event Log
      </h2>
      <span class="text-[10px] font-mono uppercase tracking-wider text-gray-400">
        {{ displayedEvents.length }} events
      </span>
    </div>

    <div class="h-64 overflow-y-auto pt-3">
      <div v-if="loading" class="text-xs text-gray-500 font-mono py-2">
        Loading events...
      </div>

      <div v-else-if="displayedEvents.length === 0" class="text-xs text-gray-500 font-mono py-2">
        No warning events found.
      </div>

      <TransitionGroup
        name="event-log"
        tag="div"
        class="relative flex flex-col"
      >
        <div
          v-for="event in displayedEvents"
          :key="event.key"
          class="border-b border-edge-dark py-2"
        >
          <div class="flex items-center justify-between gap-3">
            <div class="flex items-center gap-2">
              <span
                class="font-mono text-xs uppercase tracking-wider"
                :class="warningCodeClass(event.code)"
              >
                {{ event.code }}
              </span>
              <span
                v-if="isLiveEvent(event.triggered_at)"
                class="text-[9px] font-mono uppercase tracking-[0.25em] text-[#00ff00]"
              >
                LIVE
              </span>
            </div>
            <div class="flex items-center gap-3">
              <span
                class="text-[10px] font-mono uppercase tracking-widest"
                :class="severityClass(event.severity)"
              >
                {{ event.severity }}
              </span>
              <button
                type="button"
                class="text-[10px] font-mono uppercase tracking-[0.2em] text-gray-500 hover:text-white transition-colors"
                :aria-expanded="expandedKey === event.key"
                :aria-controls="eventDomId(event.key)"
                @click="toggleDetails(event.key)"
              >
                {{ expandedKey === event.key ? 'Hide' : 'Details' }}
              </button>
            </div>
          </div>
          <div class="text-gray-500 text-[10px] font-mono mt-1">
            {{ formatTime(event.triggered_at) }}
          </div>
          <Transition name="event-detail">
            <div
              v-if="expandedKey === event.key"
              :id="eventDomId(event.key)"
              class="mt-3 grid grid-cols-1 gap-2 text-[10px] font-mono text-gray-400 md:grid-cols-3"
            >
              <div class="flex items-center justify-between border border-edge-dark/60 px-2 py-1">
                <span class="uppercase tracking-[0.2em]">Category</span>
                <span class="text-gray-200">{{ eventCategory(event.code) }}</span>
              </div>
              <div class="flex items-center justify-between border border-edge-dark/60 px-2 py-1">
                <span class="uppercase tracking-[0.2em]">Signal</span>
                <span class="text-gray-200">{{ event.code }}</span>
              </div>
              <div class="flex items-center justify-between border border-edge-dark/60 px-2 py-1">
                <span class="uppercase tracking-[0.2em]">Triggered</span>
                <span class="text-gray-200">{{ formatTime(event.triggered_at) }}</span>
              </div>
            </div>
          </Transition>
        </div>
      </TransitionGroup>
    </div>
  </section>
</template>

<style scoped>
.event-log-enter-active,
.event-log-leave-active {
  transition: opacity 180ms ease-out, transform 180ms ease-out;
}

.event-log-enter-from {
  opacity: 0;
  transform: translateY(6px);
}

.event-log-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.event-log-move {
  transition: transform 180ms ease-out;
}

.event-detail-enter-active,
.event-detail-leave-active {
  transition: opacity 200ms ease-out, transform 200ms ease-out;
}

.event-detail-enter-from,
.event-detail-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

@media (prefers-reduced-motion: reduce) {
  .event-log-enter-active,
  .event-log-leave-active,
  .event-log-move,
  .event-detail-enter-active,
  .event-detail-leave-active {
    transition-duration: 0ms;
  }
}
</style>
