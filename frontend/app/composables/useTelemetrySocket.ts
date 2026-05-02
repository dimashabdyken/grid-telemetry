import { onUnmounted, ref } from 'vue'
// @ts-ignore TS2307 -- Nuxt alias resolution is unavailable when tsc runs with --ignoreConfig.
import type { ConnectionState, ThermalState, WSMessage, WSTelemetryMessage } from '../lib/types'

interface RuntimeConfig {
    public: {
        wsBaseUrl?: string
    }
}

declare function useRuntimeConfig(): RuntimeConfig

const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_ATTEMPTS = 5
const HEARTBEAT_TIMEOUT_MS = 30_000
const HEARTBEAT_CHECK_INTERVAL_MS = 5_000
const SMOOTHING_INTERVAL_MS = 120
const METRIC_SMOOTHING_ALPHA = 0.35

const connectionState = ref<ConnectionState>('closed')
const latestTelemetry = ref<WSTelemetryMessage['latest'] | null>(null)
const smoothedTelemetry = ref<WSTelemetryMessage['latest'] | null>(null)
const currentHealth = ref<WSTelemetryMessage['health'] | null>(null)
const thermalData = ref<ThermalState | null>(null)
const error = ref<string | null>(null)
const lastPing = ref<Date | null>(null)

const socket = ref<WebSocket | null>(null)
const reconnectAttempts = ref(0)

let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let demoTimer: ReturnType<typeof setInterval> | null = null
let heartbeatMonitorTimer: ReturnType<typeof setInterval> | null = null
let smoothingTimer: ReturnType<typeof setInterval> | null = null
let intentionalClose = false
let lastSessionKey: string | number | null = null
let lastDriverNumber: number | null = null

const clearReconnectTimer = () => {
    if (reconnectTimer) {
        clearTimeout(reconnectTimer)
        reconnectTimer = null
    }
}

const stopDemoMode = () => {
    if (demoTimer) {
        clearInterval(demoTimer)
        demoTimer = null
    }
}

const stopHeartbeatMonitor = () => {
    if (heartbeatMonitorTimer) {
        clearInterval(heartbeatMonitorTimer)
        heartbeatMonitorTimer = null
    }
}

const stopSmoothing = () => {
    if (smoothingTimer) {
        clearInterval(smoothingTimer)
        smoothingTimer = null
    }
}

const lerp = (current: number, target: number, alpha: number): number => {
    return current + (target - current) * alpha
}

const startSmoothing = () => {
    stopSmoothing()
    smoothingTimer = setInterval(() => {
        const incoming = latestTelemetry.value
        if (!incoming) {
            return
        }

        const current = smoothedTelemetry.value
        if (!current) {
            smoothedTelemetry.value = { ...incoming }
            return
        }

        smoothedTelemetry.value = {
            ...incoming,
            speed: lerp(current.speed ?? 0, incoming.speed ?? 0, METRIC_SMOOTHING_ALPHA),
            throttle: lerp(current.throttle ?? 0, incoming.throttle ?? 0, METRIC_SMOOTHING_ALPHA),
            brake: lerp(current.brake ?? 0, incoming.brake ?? 0, METRIC_SMOOTHING_ALPHA),
            rpm: lerp(current.rpm ?? 0, incoming.rpm ?? 0, METRIC_SMOOTHING_ALPHA),
            // Keep drivetrain state responsive while smoothing analog channels.
            n_gear: incoming.n_gear,
            drs: incoming.drs,
        }
    }, SMOOTHING_INTERVAL_MS)
}

const randomInt = (min: number, max: number): number =>
    Math.floor(Math.random() * (max - min + 1)) + min

const resolveBrowserWsBaseUrl = (configuredBaseUrl?: string): string => {
    if (typeof window === 'undefined') {
        return configuredBaseUrl || 'ws://localhost:8000'
    }

    const backendProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const browserBaseUrl = `${backendProtocol}//${window.location.hostname}:8000`

    if (!configuredBaseUrl) {
        return browserBaseUrl
    }

    try {
        const parsed = new URL(configuredBaseUrl)
        if (['localhost', '127.0.0.1', '0.0.0.0'].includes(parsed.hostname)) {
            return browserBaseUrl
        }
    } catch {
        return browserBaseUrl
    }

    return configuredBaseUrl
}

const createDemoThermalData = (
    sample: WSTelemetryMessage['latest'],
    tick: number
): ThermalState => {
    const cockpitTemp = Math.min(
        65,
        Math.max(
            18,
            29
            + tick * 0.05
            + Math.max(0, 180 - sample.speed) * 0.018
            + Math.max(0, sample.rpm - 9000) * 0.00055
            + sample.brake * 0.025
            - Math.min(5, sample.speed * 0.012)
        )
    )
    const seebeckWatts = Math.min(10000, (sample.brake / 100) * (sample.speed / 360) * 10000)
    const cognitiveLoad = Math.min(100, Math.max(0, 18 + Math.max(0, cockpitTemp - 32) * 4.2 + tick * 0.04))
    const pcmLoad = Math.min(100, Math.max(0, tick * 0.4 + Math.max(0, cockpitTemp - 30) * 2.4))
    const thermalAlert = cockpitTemp >= 48 || cognitiveLoad >= 85
        ? 'critical'
        : cockpitTemp >= 42 || cognitiveLoad >= 70
            ? 'warning'
            : 'none'
    const thermalRiskLaps = pcmLoad > 70 ? Math.max(0.1, (100 - pcmLoad) / 12) : null
    const drivers = [
        ...(sample.speed < 140 ? ['LOW_AIRFLOW'] : []),
        ...(cockpitTemp > 42 ? ['HIGH_COCKPIT_TEMP'] : []),
        ...(pcmLoad > 75 ? ['PCM_NEAR_LIMIT'] : []),
        ...(cognitiveLoad > 70 ? ['COGNITIVE_LOAD_HIGH'] : []),
        ...(seebeckWatts >= 1500 ? ['BRAKE_HEAT_RECOVERY'] : [])
    ]

    return {
        cockpit_temp: Number(cockpitTemp.toFixed(1)),
        pcm_load: Number(pcmLoad.toFixed(1)),
        seebeck_watts: Number(seebeckWatts.toFixed(1)),
        cognitive_load: Number(cognitiveLoad.toFixed(1)),
        thermal_alert: thermalAlert,
        auto_mode: thermalAlert === 'critical' || pcmLoad > 95,
        predicted_pcm_saturation_laps: thermalRiskLaps,
        thermal_risk_laps: thermalRiskLaps,
        drivers
    }
}

export const enableDemoMode = () => {
    intentionalClose = true
    clearReconnectTimer()
    reconnectAttempts.value = 0

    if (socket.value) {
        socket.value.close()
        socket.value = null
    }

    stopDemoMode()
    connectionState.value = 'open'
    error.value = null
    let demoTick = 0

    demoTimer = setInterval(() => {
        const throttle = randomInt(0, 100)
        const brake = throttle > 50 ? 0 : randomInt(0, 100)

        const sample = {
            date: new Date().toISOString(),
            driver_number: lastDriverNumber ?? 1,
            speed: randomInt(100, 320),
            throttle,
            brake,
            rpm: randomInt(8000, 14500),
            n_gear: randomInt(3, 8),
            drs: randomInt(0, 1)
        }
        latestTelemetry.value = sample
        smoothedTelemetry.value = sample
        thermalData.value = createDemoThermalData(sample, demoTick)
        demoTick += 1
    }, 150)
}

export const useTelemetrySocket = () => {
    const startHeartbeatMonitor = () => {
        stopHeartbeatMonitor()
        heartbeatMonitorTimer = setInterval(() => {
            if (connectionState.value !== 'open' || !socket.value) {
                return
            }

            const lastPingMs = lastPing.value?.getTime() ?? 0
            if (Date.now() - lastPingMs <= HEARTBEAT_TIMEOUT_MS) {
                return
            }

            if (socket.value.readyState === WebSocket.OPEN) {
                socket.value.close()
            }
        }, HEARTBEAT_CHECK_INTERVAL_MS)
    }

    const scheduleReconnect = () => {
        if (
            intentionalClose ||
            reconnectAttempts.value >= MAX_RECONNECT_ATTEMPTS ||
            lastSessionKey === null ||
            lastDriverNumber === null
        ) {
            connectionState.value = 'closed'
            return
        }

        reconnectAttempts.value += 1
        connectionState.value = 'reconnecting'
        clearReconnectTimer()
        reconnectTimer = setTimeout(() => {
            connect(lastSessionKey as string | number, lastDriverNumber as number)
        }, RECONNECT_DELAY_MS)
    }

    const handleMessage = (rawMessage: string) => {
        let parsedMessage: WSMessage

        try {
            parsedMessage = JSON.parse(rawMessage) as WSMessage
        } catch {
            error.value = 'Received invalid WebSocket message payload.'
            return
        }

        switch (parsedMessage.type) {
            case 'connected':
                console.log(
                    `Telemetry socket connected for session ${parsedMessage.session_key}, driver ${parsedMessage.driver_number}.`
                )
                break
            case 'telemetry':
                latestTelemetry.value = {
                    ...parsedMessage.latest,
                    ...(parsedMessage.timestamp ? { timestamp: parsedMessage.timestamp } : {}),
                }
                currentHealth.value = parsedMessage.health
                thermalData.value = parsedMessage.thermal ?? null
                break
            case 'ping':
                lastPing.value = new Date()
                if (socket.value?.readyState === WebSocket.OPEN) {
                    socket.value.send(JSON.stringify({ type: 'pong' }))
                }
                break
            case 'error':
                error.value = parsedMessage.message
                break
            default:
                error.value = 'Received unsupported WebSocket message type.'
        }
    }

    const connect = (sessionKey: string | number, driverNumber: number) => {
        const config = useRuntimeConfig()
        const WS_BASE = resolveBrowserWsBaseUrl(config.public.wsBaseUrl)

        stopDemoMode()
        startSmoothing()

        lastSessionKey = sessionKey
        lastDriverNumber = driverNumber

        intentionalClose = false
        clearReconnectTimer()

        if (socket.value) {
            socket.value.close()
            socket.value = null
        }

        connectionState.value = 'connecting'

        const url = `${WS_BASE}/ws/telemetry/${sessionKey}/${driverNumber}`
        const ws = new WebSocket(url)
        socket.value = ws

        ws.onopen = () => {
            connectionState.value = 'open'
            error.value = null
            reconnectAttempts.value = 0
            lastPing.value = new Date()
            startHeartbeatMonitor()
        }

        ws.onclose = () => {
            socket.value = null
            stopHeartbeatMonitor()
            scheduleReconnect()
        }

        ws.onerror = () => {
            error.value = 'WebSocket connection error. Please try reconnecting.'
        }

        ws.onmessage = (event: MessageEvent<string>) => {
            handleMessage(event.data)
        }
    }

    const disconnect = () => {
        intentionalClose = true
        clearReconnectTimer()
        stopDemoMode()
        stopHeartbeatMonitor()
        stopSmoothing()
        reconnectAttempts.value = 0

        if (socket.value) {
            socket.value.close()
            socket.value = null
        }

        connectionState.value = 'closed'
        latestTelemetry.value = null
        smoothedTelemetry.value = null
        currentHealth.value = null
        thermalData.value = null
        error.value = null
        lastPing.value = null
    }

    onUnmounted(() => {
        disconnect()
    })

    return {
        connectionState,
        latestTelemetry,
        smoothedTelemetry,
        currentHealth,
        thermalData,
        error,
        lastPing,
        connect,
        disconnect
    }
}
