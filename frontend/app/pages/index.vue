  <script setup lang="ts">
  import { onMounted, onUnmounted, ref } from 'vue'
  import { getDrivers, getSession, getTyreStatus } from '~/lib/api'
  import DriverCard from '~/components/DriverCard.vue'
  import HealthScoreRing from '~/components/HealthScoreRing.vue'
  import MasterWarningPanel from '~/components/MasterWarningPanel.vue'
  import TelemetryChart from '~/components/TelemetryChart.vue'
  import TelemetryGauges from '~/components/TelemetryGauges.vue'
  import TrackMap from '~/components/TrackMap.vue'
  import TyreStatusCard from '~/components/TyreStatusCard.vue'
  import WarningHistoryPanel from '~/components/WarningHistoryPanel.vue'
  import { useHealthScore } from '~/composables/useHealthScore'
  import { useTelemetrySocket } from '~/composables/useTelemetrySocket'

  const sessionInfo = ref<Awaited<ReturnType<typeof getSession>> | null>(null)
  const driverNumber = ref(1)
  const driverInfo = ref<any>(null)
  const tyreInfo = ref<any>(null)

  const {
    connect,
    disconnect,
    connectionState,
    latestTelemetry,
    smoothedTelemetry,
    currentHealth,
    error
  } = useTelemetrySocket()

  const { score, warnings, highestSeverity } = useHealthScore(currentHealth)

  onMounted(async () => {
    connect(9161, 1)
    try {
      sessionInfo.value = await getSession(9161)
      tyreInfo.value = await getTyreStatus(9161, 1)
    } catch {
      error.value = 'Backend connection failed. Please ensure the backend is running.'
    }

    try {
      const allDrivers = await getDrivers(9161)
      driverInfo.value = allDrivers.find(d => d.driver_number === driverNumber.value) || null
    } catch (e) {
      console.warn('Failed to fetch drivers')
    }

    if (!tyreInfo.value) {
      try {
        tyreInfo.value = await getTyreStatus(9161, 1)
      } catch {
        console.warn('Failed to fetch tyre status')
      }
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
        <h1 class="text-2xl font-black tracking-tighter uppercase text-white flex items-center gap-3">
          Grid Telemetry
          <span v-if="sessionInfo" class="text-gray-500 font-normal text-lg">| Singapore Grand Prix</span>
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

        <main class="p-6 max-w-7xl mx-auto flex flex-col gap-6">
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 items-stretch">
          <DriverCard :driver="driverInfo" />
          <TyreStatusCard :tyre-status="tyreInfo" />
            <section class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg h-full">
            <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold mb-2">System Health</h2>
            <div class="flex flex-col items-center justify-center flex-1">
              <HealthScoreRing :score="score" :severity="highestSeverity || 'NORMAL'" />
            </div>
          </section>
            <section class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 flex flex-col gap-4 shadow-lg h-full">
            <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold">Telemetry Stream</h2>
            <div v-if="!latestTelemetry" class="flex flex-col items-center justify-center h-48 text-gray-500">
              <p class="text-lg font-bold uppercase tracking-widest">Waiting for data...</p>
            </div>
            <div v-else class="grid grid-cols-1">
              <TelemetryGauges :data="smoothedTelemetry" />
            </div>
          </section>
        </div>

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 items-stretch">
            <div class="h-[320px] h-full">
              <div v-if="!latestTelemetry" class="flex flex-col items-center justify-center h-full text-gray-500 bg-[#1e1e28] rounded-xl p-4 border border-white/5 shadow-lg">
              <p class="text-lg font-bold uppercase tracking-widest">Waiting for data...</p>
            </div>
            <TrackMap v-else :telemetry="latestTelemetry" :team-color="driverInfo?.team_colour" :driver-acronym="driverInfo?.name_acronym" />
          </div>

            <section class="bg-[#1e1e28] rounded-xl p-6 border border-white/5 shadow-lg h-[320px] h-full flex flex-col">
            <h2 class="text-sm text-gray-400 uppercase tracking-widest font-bold mb-4">Speed Trend</h2>
            <div v-if="!latestTelemetry" class="flex flex-col items-center justify-center flex-1 text-gray-500">
              <p class="text-lg font-bold uppercase tracking-widest">Waiting for data...</p>
            </div>
            <div v-else class="min-h-0 flex-1">
              <TelemetryChart :data="smoothedTelemetry" />
            </div>
          </section>
        </div>

        <div class="w-full">
          <WarningHistoryPanel />
        </div>
      </main>
    </div>
  </template>
