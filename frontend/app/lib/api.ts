interface RuntimeConfig {
    public: {
        apiBaseUrl?: string
    }
}

declare function useRuntimeConfig(): RuntimeConfig

// @ts-ignore TS2307 -- Nuxt alias resolution is unavailable when tsc runs with --ignoreConfig.
import type { F1Driver, F1Session, HealthCheckResponse, TelemetryResponse } from './types'

export interface WarningEvent {
    code: string
    severity: string
    triggered_at: string
}

export interface TyreStatus {
    compound: string
    life: number
}

export class ApiError extends Error {
    constructor(
        message: string,
        public status: number,
        public endpoint: string
    ) {
        super(message)
        this.name = 'ApiError'
    }
}

function buildUrl(
    endpoint: string,
    params: Record<string, string | number | boolean | undefined>
): string {
    const searchParams = new URLSearchParams()

    for (const [key, value] of Object.entries(params)) {
        if (value !== undefined) {
            searchParams.set(key, String(value))
        }
    }

    const queryString = searchParams.toString()
    return queryString ? `${endpoint}?${queryString}` : endpoint
}

function resolveBrowserBaseUrl(configuredBaseUrl?: string): string {
    if (typeof window === 'undefined') {
        return configuredBaseUrl || 'http://localhost:8000'
    }

    const backendProtocol = window.location.protocol === 'https:' ? 'https:' : 'http:'
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

async function apiFetch<T>(
    endpoint: string,
    options?: RequestInit
): Promise<T> {
    const config = useRuntimeConfig()
    const BASE_URL = resolveBrowserBaseUrl(config.public.apiBaseUrl)
    const method = (options?.method || 'GET').toUpperCase()

    const headers = new Headers(options?.headers)
    const hasBody = options?.body !== undefined && options?.body !== null
    if (hasBody && !headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
    }
    if (!headers.has('Accept')) {
        headers.set('Accept', 'application/json')
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
        method,
        headers
    })

    if (!response.ok) {
        let detail = response.statusText

        try {
            const errorBody = await response.text()
            if (errorBody) {
                detail = errorBody
            }
        } catch {
            // Keep the default status text if body parsing fails.
        }

        throw new ApiError(
            `Request failed for ${endpoint} with status ${response.status}: ${detail}`,
            response.status,
            endpoint
        )
    }

    return (await response.json()) as T
}

/**
 * Calls GET /api/v1/sessions/{sessionKey} and returns the matching F1 session.
 */
export async function getSession(sessionKey: number | string): Promise<F1Session> {
    return apiFetch<F1Session>(`/api/v1/sessions/${sessionKey}`)
}

/**
 * Calls GET /api/v1/telemetry and returns telemetry records and optional health data.
 */
export async function getTelemetry(
    sessionKey: string | number = 'latest',
    driverNumber?: number,
    includeHealth: boolean = true
): Promise<TelemetryResponse> {
    const endpoint = buildUrl('/api/v1/telemetry', {
        session_key: sessionKey,
        driver_number: driverNumber,
        include_health: includeHealth
    })

    return apiFetch<TelemetryResponse>(endpoint)
}

/**
 * Calls GET /api/v1/drivers and returns all drivers for the given session.
 */
export async function getDrivers(
    sessionKey: string | number = 'latest'
): Promise<F1Driver[]> {
    const endpoint = buildUrl('/api/v1/drivers', {
        session_key: sessionKey
    })

    const payload = await apiFetch<
        F1Driver[] | { drivers?: F1Driver[] }
    >(endpoint)

    if (Array.isArray(payload)) {
        return payload
    }

    return Array.isArray(payload.drivers) ? payload.drivers : []
}

/**
 * Calls GET /health and returns backend health-check status.
 */
export async function getHealthCheck(): Promise<HealthCheckResponse> {
    return apiFetch<HealthCheckResponse>('/health')
}

/**
 * Calls GET /api/v1/warnings/history and returns warning events.
 */
export async function getWarningsHistory(
    sessionKey: string | number = 9161,
    limit: number = 10
): Promise<WarningEvent[]> {
    const endpoint = buildUrl('/api/v1/warnings/history', {
        session_key: sessionKey,
        limit
    })

    return apiFetch<WarningEvent[]>(endpoint)
}

export async function getTyreStatus(
    sessionKey: string | number = 'latest',
    driverNumber: number = 1
): Promise<TyreStatus> {
    return apiFetch<TyreStatus>(
        buildUrl('/api/v1/tyres', {
            session_key: sessionKey,
            driver_number: driverNumber
        })
    )
}

export async function getCircuitPath(
    sessionKey: string | number
): Promise<{ x: number; y: number }[]> {
    const payload = await apiFetch<{
        path?: { x: number; y: number }[]
    }>(`/api/v1/circuit/${sessionKey}`)

    return Array.isArray(payload.path) ? payload.path : []
}
