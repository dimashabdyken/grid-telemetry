import { computed, type Ref } from 'vue'
// @ts-ignore TS2307 -- Nuxt alias resolution is unavailable when tsc runs with --ignoreConfig.
import type { ThermalState } from '../lib/types'

export const useThermalState = (thermalData: Ref<ThermalState | null>) => {
    const cockpitTempDisplay = computed(() => {
        const cockpitTemp = thermalData.value?.cockpit_temp ?? 0
        return `${cockpitTemp.toFixed(1)}°C`
    })

    const pcmPercent = computed(() => {
        return Math.max(0, Math.min(100, thermalData.value?.pcm_load ?? 0))
    })

    const seebeckDisplay = computed(() => {
        const seebeckKilowatts = (thermalData.value?.seebeck_watts ?? 0) / 1000
        return `${seebeckKilowatts.toFixed(1)} kW`
    })

    const cognitivePercent = computed(() => {
        const cognitiveLoad = thermalData.value?.cognitive_load ?? 0
        return Math.max(0, Math.min(100, 100 - cognitiveLoad))
    })

    const alertLevel = computed(() => {
        return thermalData.value?.thermal_alert ?? thermalData.value?.alert ?? 'none'
    })

    const alertColor = computed(() => {
        if (alertLevel.value === 'critical') {
            return 'text-red-500'
        }

        if (alertLevel.value === 'warning') {
            return 'text-yellow-400'
        }

        return ''
    })

    const riskForecastDisplay = computed(() => {
        const riskLaps = thermalData.value?.thermal_risk_laps
        if (riskLaps === null || riskLaps === undefined) {
            return 'THERMAL TREND STABLE'
        }

        return `RISK IN ${riskLaps.toFixed(1)} LAPS`
    })

    const pcmForecastDisplay = computed(() => {
        const pcmLaps = thermalData.value?.predicted_pcm_saturation_laps
        if (pcmLaps === null || pcmLaps === undefined) {
            return 'PCM BUFFER STABLE'
        }

        return `PCM SATURATION IN ${pcmLaps.toFixed(1)} LAPS`
    })

    const driverCauseDisplay = computed(() => {
        const drivers = thermalData.value?.drivers ?? []
        if (drivers.length === 0) {
            return 'CAUSE: NOMINAL THERMAL FLOW'
        }

        return `CAUSE: ${drivers.slice(0, 3).join(' / ')}`
    })

    return {
        cockpitTempDisplay,
        pcmPercent,
        seebeckDisplay,
        cognitivePercent,
        alertLevel,
        alertColor,
        riskForecastDisplay,
        pcmForecastDisplay,
        driverCauseDisplay
    }
}
