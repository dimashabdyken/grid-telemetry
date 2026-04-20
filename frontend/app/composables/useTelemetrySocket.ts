import { onUnmounted, ref } from 'vue'
// @ts-ignore TS2307 -- Nuxt alias resolution is unavailable when tsc runs with --ignoreConfig.
import type { ConnectionState, WSMessage, WSTelemetryMessage } from '../lib/types'

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

const connectionState = ref<ConnectionState>('closed')
const latestTelemetry = ref<WSTelemetryMessage['latest'] | null>(null)
const currentHealth = ref<WSTelemetryMessage['health'] | null>(null)
const error = ref<string | null>(null)
const lastPing = ref<Date | null>(null)

const socket = ref<WebSocket | null>(null)
const reconnectAttempts = ref(0)

let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let demoTimer: ReturnType<typeof setInterval> | null = null
let heartbeatMonitorTimer: ReturnType<typeof setInterval> | null = null
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

const randomInt = (min: number, max: number): number =>
    Math.floor(Math.random() * (max - min + 1)) + min

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

    demoTimer = setInterval(() => {
        const throttle = randomInt(0, 100)
        const brake = throttle > 50 ? 0 : randomInt(0, 100)

        latestTelemetry.value = {
            date: new Date().toISOString(),
            driver_number: lastDriverNumber ?? 1,
            speed: randomInt(100, 320),
            throttle,
            brake,
            rpm: randomInt(8000, 14500),
            n_gear: randomInt(3, 8),
            drs: randomInt(0, 1)
        }
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
                latestTelemetry.value = parsedMessage.latest
                currentHealth.value = parsedMessage.health
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
        const WS_BASE = config.public.wsBaseUrl || 'ws://localhost:8000'

        stopDemoMode()

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
        reconnectAttempts.value = 0

        if (socket.value) {
            socket.value.close()
            socket.value = null
        }

        connectionState.value = 'closed'
        latestTelemetry.value = null
        currentHealth.value = null
        error.value = null
        lastPing.value = null
    }

    onUnmounted(() => {
        disconnect()
    })

    return {
        connectionState,
        latestTelemetry,
        currentHealth,
        error,
        lastPing,
        connect,
        disconnect
    }
}
