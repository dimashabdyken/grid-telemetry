interface RuntimeConfig {
    public: {
        apiBaseUrl?: string
    }
}

declare function useRuntimeConfig(): RuntimeConfig

// @ts-ignore TS2307 -- Nuxt alias resolution is unavailable when tsc runs with --ignoreConfig.
import type { F1Driver, F1Session, HealthCheckResponse, TelemetryResponse } from '~/lib/types.ts'

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

async function apiFetch<T>(
    endpoint: string,
    options?: RequestInit
): Promise<T> {
    const config = useRuntimeConfig()
    const BASE_URL = config.public.apiBaseUrl || 'http://localhost:8000'

    const headers = new Headers(options?.headers)
    if (!headers.has('Content-Type')) {
        headers.set('Content-Type', 'application/json')
    }

    const response = await fetch(`${BASE_URL}${endpoint}`, {
        ...options,
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
 * Calls GET /api/v1/sessions/latest and returns the latest available F1 session.
 */
export async function getLatestSession(): Promise<F1Session> {
    return apiFetch<F1Session>('/api/v1/sessions/latest')
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

    return apiFetch<F1Driver[]>(endpoint)
}

/**
 * Calls GET /health and returns backend health-check status.
 */
export async function getHealthCheck(): Promise<HealthCheckResponse> {
    return apiFetch<HealthCheckResponse>('/health')
}
