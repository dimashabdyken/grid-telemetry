/**
 * Represents an F1 session returned by the backend sessions endpoint.
 */
export interface F1Session {
    session_key: number
    session_name: string
    session_type: string
    date_start: string
    date_end: string
    circuit_short_name: string
    country_name: string
    location: string
    year: number
    meeting_key: number
}

/**
 * Represents an F1 driver returned by the backend drivers endpoint.
 */
export interface F1Driver {
    driver_number: number
    full_name: string
    name_acronym: string
    team_name: string
    team_colour: string
    country_code: string
    headshot_url: string | null
}

/**
 * Represents a single telemetry record for a driver car data point.
 */
export interface CarDataRecord {
    date: string
    driver_number: number
    speed: number
    throttle: number
    brake: number
    rpm: number
    n_gear: number
    drs: number
    _id?: number
}

/**
 * Represents the latest reduced vehicle telemetry snapshot used for health scoring.
 */
export interface VehicleSnapshot {
    throttle: number
    brake: number
    rpm: number
    speed: number
    gear: number
    drs: number
}

export type WarningSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW'

export type WarningCode =
    | 'NO_DATA'
    | 'RPM_REDLINE_BREACH'
    | 'HEAVY_BRAKE_EVENT'
    | 'STUCK_THROTTLE_STATIONARY'
    | 'SUSTAINED_WOT'
    | 'DRS_FAULT'
    | 'POSSIBLE_MISSED_GEAR'

/**
 * Represents a computed vehicle health score with warnings and snapshot context.
 */
export interface HealthScore {
    score: number
    warnings: WarningCode[]
    snapshot: VehicleSnapshot
    timestamp: string
}

export type WSMessageType = 'telemetry' | 'error' | 'ping' | 'connected'

/**
 * Represents the initial websocket connected acknowledgement payload.
 */
export interface WSConnectedMessage {
    type: 'connected'
    session_key: string
    driver_number: number
    message: string
}

/**
 * Represents a websocket telemetry update payload.
 */
export interface WSTelemetryMessage {
    type: 'telemetry'
    session_key: string
    driver_number: number
    health: HealthScore
    new_records: number
    latest: CarDataRecord
}

/**
 * Represents a websocket error payload.
 */
export interface WSErrorMessage {
    type: 'error'
    message: string
}

/**
 * Represents a websocket heartbeat payload.
 */
export interface WSPingMessage {
    type: 'ping'
}

export type WSMessage =
    | WSConnectedMessage
    | WSTelemetryMessage
    | WSErrorMessage
    | WSPingMessage

/**
 * Represents the telemetry API response for historical and latest data.
 */
export interface TelemetryResponse {
    session_key: string
    driver_number: number | null
    record_count: number
    records: CarDataRecord[]
    health?: HealthScore
}

/**
 * Represents the backend health-check API response.
 */
export interface HealthCheckResponse {
    app: string
    version: string
    debug: boolean
    redis: boolean
}

export type ConnectionState =
    | 'connecting'
    | 'open'
    | 'reconnecting'
    | 'closed'
