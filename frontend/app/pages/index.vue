  <script setup lang="ts">
  import { onMounted, onUnmounted, ref } from 'vue'
  import { getDrivers, getSession, getTyreStatus } from '~/lib/api'
  import CarVisualizer from '~/components/CarVisualizer.vue'
  import DriverCard from '~/components/DriverCard.vue'
  import HealthScoreRing from '~/components/HealthScoreRing.vue'
  import LightSpeedBackground from '~/components/LightSpeedBackground.vue'
  import MasterWarningPanel from '~/components/MasterWarningPanel.vue'
  import TelemetryChart from '~/components/TelemetryChart.vue'
  import TelemetryGauges from '~/components/TelemetryGauges.vue'
  import ThermalPanel from '~/components/ThermalPanel.vue'
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
    thermalData,
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
    <div class="relative isolate min-h-screen overflow-hidden bg-transparent text-slate-100 font-sans">
      <LightSpeedBackground />

      <header
        class="relative z-10 border-b border-white/10 border-t-4 border-t-[#e10600] bg-black/40 px-6 py-4 flex items-center justify-between"
      >
        <h1 class="text-2xl font-black tracking-tighter uppercase text-white flex items-center gap-3">
          Grid Telemetry
          <span v-if="sessionInfo" class="text-gray-500 font-normal text-lg">| Singapore Grand Prix</span>
        </h1>

        <div class="flex items-center gap-3">
          <div class="flex items-center gap-2 rounded-full border border-white/10 px-3 py-1 text-xs font-bold uppercase tracking-wider">
            <span class="h-2 w-2 rounded-full" :class="connectionState === 'open' ? 'bg-[#00ff00]' : 'bg-gray-500'" />
            <span :class="connectionState === 'open' ? 'text-[#00ff00]' : 'text-gray-400'">
              {{ connectionState }}
            </span>
          </div>
        </div>
      </header>

      <div class="relative z-10 mx-auto max-w-[1600px] px-6 pt-6 xl:px-8">
        <MasterWarningPanel :warnings="warnings" />
      </div>

        <main class="relative z-10 mx-auto flex max-w-[1600px] flex-col gap-6 p-6 xl:px-8">
          <div class="grid grid-cols-1 items-stretch gap-6 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
          <DriverCard
            :driver="driverInfo"
            :live-position="currentHealth?.snapshot?.position"
            :live-gap="currentHealth?.snapshot?.gap"
            :live-pit-stops="currentHealth?.snapshot?.pit_stops"
            class="h-full"
          />
          <TyreStatusCard
            :tyre-status="tyreInfo"
            :live-compound="currentHealth?.snapshot?.tyre_compound"
            :live-life="currentHealth?.snapshot?.tyre_life"
            class="h-full"
          />
          <section class="bg-surface border border-edge p-5 flex flex-col gap-4 h-full">
            <div class="flex items-center justify-between border-b border-edge-dark pb-2">
              <h2 class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono">
                System Health
              </h2>
              <span
                class="text-[10px] font-mono uppercase tracking-wider text-gray-400"
              >
                Severity: {{ highestSeverity || 'NORMAL' }}
              </span>
            </div>
            <div class="flex flex-1 items-center justify-center">
              <HealthScoreRing
                :score="score"
                :severity="highestSeverity || 'NORMAL'"
                :current-health="currentHealth"
              />
            </div>
          </section>
          <ThermalPanel
            :thermal-data="thermalData"
            class="h-full"
          />
            <section class="bg-surface border border-edge p-5 flex flex-col gap-3 h-full">
              <div class="flex items-center justify-between border-b border-edge-dark pb-2">
                <h2 class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono">
                  Telemetry Stream
                </h2>
                <span class="text-[10px] font-mono uppercase tracking-wider text-gray-400">
                  {{ latestTelemetry ? 'Live' : 'Standby' }}
                </span>
              </div>
              <div v-if="!latestTelemetry" class="flex flex-1 items-center justify-center text-gray-500">
                <p class="text-xs font-mono uppercase tracking-[0.2em]">Waiting for data</p>
              </div>
              <div v-else class="min-h-0 flex-1">
                <TelemetryGauges :data="smoothedTelemetry" />
              </div>
            </section>
        </div>

        <CarVisualizer />

          <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <section class="bg-surface border border-edge p-5 h-[320px] flex flex-col gap-3">
              <div class="flex items-center justify-between border-b border-edge-dark pb-2">
                <h2 class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono">
                  Track Map
                </h2>
                <span class="text-[10px] font-mono uppercase tracking-wider text-gray-400">
                  {{ latestTelemetry ? 'Live' : 'Standby' }}
                </span>
              </div>
              <div v-if="!latestTelemetry" class="flex flex-1 items-center justify-center text-gray-500">
                <p class="text-xs font-mono uppercase tracking-[0.2em]">Waiting for data</p>
              </div>
              <div v-else class="min-h-0 flex-1">
                <TrackMap
                  :telemetry="latestTelemetry"
                  :team-color="driverInfo?.team_colour"
                  :driver-acronym="driverInfo?.name_acronym"
                />
              </div>
            </section>

          <section class="bg-surface border border-edge p-5 h-[320px] flex flex-col gap-3">
            <div class="flex items-center justify-between border-b border-edge-dark pb-2">
              <h2 class="text-[10px] text-gray-400 uppercase tracking-[0.2em] font-mono">
                Speed Trend
              </h2>
              <span class="text-[10px] font-mono uppercase tracking-wider text-gray-400">
                {{ latestTelemetry ? 'Live' : 'Standby' }}
              </span>
            </div>
            <div v-if="!latestTelemetry" class="flex flex-1 items-center justify-center text-gray-500">
              <p class="text-xs font-mono uppercase tracking-[0.2em]">Waiting for data</p>
            </div>
            <div v-else class="min-h-0 flex-1">
              <TelemetryChart :data="smoothedTelemetry" />
            </div>
          </section>
        </div>

        <div class="w-full">
          <WarningHistoryPanel :live-warnings="warnings" />
        </div>
      </main>
    </div>
  </template>
