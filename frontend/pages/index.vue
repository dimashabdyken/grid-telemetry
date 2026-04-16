<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useHealthScore, useTelemetrySocket } from '#imports'
import { getLatestSession } from '~/lib/api'

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

const healthState = useHealthScore(currentHealth)

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
  <main>
    <h1>Grid Telemetry - Pipeline Test</h1>

    <section>
      <h2>Connection Status</h2>
      <p>State: {{ connectionState }}</p>
      <p v-if="error">Error: {{ error }}</p>
    </section>

    <section>
      <h2>Session Info</h2>
      <p>Name: {{ sessionInfo?.session_name ?? 'Loading...' }}</p>
      <p>Year: {{ sessionInfo?.year ?? '-' }}</p>
    </section>

    <section>
      <h2>Vehicle Health</h2>
      <p>Score: {{ healthState.score }}</p>
      <p>Warnings: {{ healthState.warnings }}</p>
    </section>

    <section>
      <h2>Raw Telemetry</h2>
      <pre>{{ latestTelemetry }}</pre>
    </section>
  </main>
</template>
