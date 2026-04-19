<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { getDrivers, getSession } from '~~/lib/api'
import DriverCard from '~~/components/DriverCard.vue'
import HealthScoreRing from '~~/components/HealthScoreRing.vue'
import MasterWarningPanel from '~~/components/MasterWarningPanel.vue'
import TelemetryGauges from '~~/components/TelemetryGauges.vue'
import { useHealthScore } from '~~/composables/useHealthScore'
import { enableDemoMode, useTelemetrySocket } from '~~/composables/useTelemetrySocket'

const sessionInfo = ref<Awaited<ReturnType<typeof getSession>> | null>(null)
const driverNumber = ref(1)
const driverInfo = ref<any>(null)

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
  connect(9161, 1)
  try {
    sessionInfo.value = await getSession(9161)
  } catch (mountError) {
    console.warn('Backend offline, starting DEMO MODE for UI development')
    sessionInfo.value = { session_name: 'Singapore GP (DEMO)', year: 2023 } as any
    driverInfo.value = {
      full_name: 'Max Verstappen',
      team_name: 'Red Bull Racing',
      driver_number: 1,
      team_colour: '3671C6',
      headshot_url: 'https://media.formula1.com/d_driver_fallback_image.png/content/dam/fom-website/drivers/M/MAXVER01_Max_Verstappen/maxver01.png.transform/2col/image.png'
    } as any
    enableDemoMode()
  }

  try {
    const allDrivers = await getDrivers(9161)
    driverInfo.value = allDrivers.find(d => d.driver_number === driverNumber.value) || null
  } catch (e) {
    console.warn('Failed to fetch drivers')
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

    <div class="max-w-7xl mx-auto px-6 pt-6">
      <MasterWarningPanel :warnings="warnings" />
    </div>

    <main class="p-6 max-w-7xl mx-auto grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <DriverCard :driver="driverInfo" />

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
        </div>
      </section>

      <section
        class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg"
      >
        <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">
          Telemetry Stream
        </h2>
        <TelemetryGauges :data="latestTelemetry" />
      </section>
    </main>
  </div>
</template>
