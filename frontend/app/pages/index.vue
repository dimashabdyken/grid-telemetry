<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { getLatestSession } from '~~/lib/api'
import HealthScoreRing from '~~/components/HealthScoreRing.vue'
import { useHealthScore } from '~~/composables/useHealthScore'
import { useTelemetrySocket } from '~~/composables/useTelemetrySocket'

const sessionInfo = ref<Awaited<ReturnType<typeof getLatestSession>> | null>(null)
const driverNumber = ref(1)

const {
  connect,
  disconnect,
  connectionState,
  latestTelemetry,
  currentHealth,
  error
} = useTelemetrySocket()

const { score, warnings, highestSeverity } = useHealthScore(currentHealth)

onMounted(async () => {
  try {
    sessionInfo.value = await getLatestSession()
    connect(sessionInfo.value.session_key, driverNumber.value)
  } catch (mountError) {
    const message =
      mountError instanceof Error
        ? mountError.message
        : 'Failed to initialize telemetry pipeline.'
    error.value = message
  }
})

onUnmounted(() => {
  disconnect()
})
</script>

<template>
  <div class="min-h-screen bg-[#15151e] text-slate-100 font-sans">
    <header
      class="border-b border-white/10 border-t-4 border-t-[#e10600] bg-black/40 px-6 py-4 flex items-center justify-between"
    >
      <h1 class="text-2xl font-black tracking-tighter uppercase text-white">
        Grid Telemetry
      </h1>

      <div class="flex items-center gap-2 rounded-full border border-white/10 px-3 py-1 text-xs font-bold uppercase tracking-wider">
        <span class="h-2 w-2 rounded-full" :class="connectionState === 'open' ? 'bg-[#00ff00]' : 'bg-gray-500'" />
        <span :class="connectionState === 'open' ? 'text-[#00ff00]' : 'text-gray-400'">
          {{ connectionState }}
        </span>
      </div>
    </header>

    <main class="p-6 max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-6">
      <section
        class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg"
      >
        <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">
          Session
        </h2>
        <div class="space-y-1">
          <p class="text-3xl font-black tracking-tight text-white">
            {{ sessionInfo?.session_name ?? 'Loading...' }}
          </p>
          <p class="text-xl font-extrabold text-slate-200">
            {{ sessionInfo?.year ?? '-' }}
          </p>
        </div>
        <p v-if="error" class="text-[#e10600] text-xs font-bold uppercase tracking-wide">
          {{ error }}
        </p>
      </section>

      <section
        class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg"
      >
        <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold mb-2">
          System Health
        </h2>
        <div class="flex flex-col items-center justify-center flex-1">
          <HealthScoreRing
            :score="score"
            :severity="highestSeverity || 'NORMAL'"
          />
          <ul
            v-if="warnings && warnings.length"
            class="mt-4 space-y-1 text-center"
          >
            <li
              v-for="warning in warnings"
              :key="warning"
              class="text-[#e10600] text-xs font-bold"
            >
              {{ warning }}
            </li>
          </ul>
        </div>
      </section>

      <section
        class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg"
      >
        <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">
          Telemetry Stream
        </h2>
        <div class="bg-black/60 rounded p-4 overflow-x-auto h-48">
          <pre class="text-xs text-[#00ff00] tabular-nums">{{ latestTelemetry }}</pre>
        </div>
      </section>
    </main>
  </div>
</template>
