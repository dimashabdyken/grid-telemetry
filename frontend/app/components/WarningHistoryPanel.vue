<script setup lang="ts">
import { onMounted, ref } from 'vue'

interface WarningEvent {
  code: string
  severity: string
  triggered_at: string
}

const events = ref<WarningEvent[]>([])
const loading = ref(true)

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

onMounted(async () => {
  try {
    const response = await fetch('/api/v1/warnings/history')
    if (!response.ok) {
      throw new Error(`Request failed with status ${response.status}`)
    }
    const data = (await response.json()) as WarningEvent[]
    events.value = Array.isArray(data) ? data : []
  } catch {
    events.value = []
  } finally {
    loading.value = false
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

      <div v-else-if="events.length === 0" class="text-sm text-gray-500 py-2">
        No warning events found.
      </div>

      <div
        v-for="(event, index) in events"
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
