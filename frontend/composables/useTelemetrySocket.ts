import { onUnmounted, ref } from 'vue'
// @ts-ignore TS2307 -- Nuxt alias resolution is unavailable when tsc runs with --ignoreConfig.
import type { ConnectionState, WSMessage, WSTelemetryMessage } from '~/lib/types'

interface RuntimeConfig {
    public: {
        wsBaseUrl?: string
    }
}

declare function useRuntimeConfig(): RuntimeConfig

const RECONNECT_DELAY_MS = 2000
const MAX_RECONNECT_ATTEMPTS = 5

export const useTelemetrySocket = () => {
    const connectionState = ref<ConnectionState>('closed')
    const latestTelemetry = ref<WSTelemetryMessage['latest'] | null>(null)
    const currentHealth = ref<WSTelemetryMessage['health'] | null>(null)
    const error = ref<string | null>(null)
    const lastPing = ref<Date | null>(null)

    const socket = ref<WebSocket | null>(null)
    const reconnectAttempts = ref(0)

    let reconnectTimer: ReturnType<typeof setTimeout> | null = null
    let intentionalClose = false
    let lastSessionKey: string | number | null = null
    let lastDriverNumber: number | null = null

    const clearReconnectTimer = () => {
        if (reconnectTimer) {
            clearTimeout(reconnectTimer)
            reconnectTimer = null
        }
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
        }

        ws.onclose = () => {
            socket.value = null
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
