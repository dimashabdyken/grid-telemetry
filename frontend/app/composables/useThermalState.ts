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

    const forecastWindowDisplay = (
        value: number | null | undefined,
        stableText: string,
        imminentText: string,
        prefix: string
    ) => {
        if (value === null || value === undefined) {
            return stableText
        }

        if (value <= 1) {
            return imminentText
        }

        if (value <= 2) {
            return `${prefix} WITHIN 2 LAPS`
        }

        if (value <= 4) {
            return `${prefix} IN 2-4 LAPS`
        }

        if (value <= 8) {
            return `${prefix} IN 4-8 LAPS`
        }

        return stableText
    }

    const riskForecastDisplay = computed(() => {
        return forecastWindowDisplay(
            thermalData.value?.thermal_risk_laps,
            'THERMAL TREND STABLE',
            'THERMAL RISK IMMINENT',
            'THERMAL RISK'
        )
    })

    const pcmForecastDisplay = computed(() => {
        return forecastWindowDisplay(
            thermalData.value?.predicted_pcm_saturation_laps,
            'PCM BUFFER STABLE',
            'PCM SATURATION IMMINENT',
            'PCM SATURATION'
        )
    })

    const formatCause = (cause: string) => {
        return cause.replaceAll('_', ' ').toUpperCase()
    }

    const driverCauseDisplay = computed(() => {
        const drivers = thermalData.value?.drivers ?? []
        if (drivers.length === 0) {
            return 'CAUSE: NOMINAL THERMAL FLOW'
        }

        return `CAUSE: ${drivers.slice(0, 3).map(formatCause).join(' / ')}`
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
