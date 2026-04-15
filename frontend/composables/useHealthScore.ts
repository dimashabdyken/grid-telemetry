import { computed, type Ref } from 'vue'
// @ts-ignore TS2307 -- Nuxt alias resolution is unavailable when tsc runs with --ignoreConfig.
import type { HealthScore } from '~/lib/types'

const CRITICAL_WARNING_CODES = new Set<string>([
  'NO_DATA',
  'RPM_REDLINE_BREACH',
  'DRS_FAULT'
])

const HIGH_WARNING_CODES = new Set<string>([
  'HEAVY_BRAKE_EVENT',
  'STUCK_THROTTLE_STATIONARY',
  'SUSTAINED_WOT',
  'POSSIBLE_MISSED_GEAR'
])

export const useHealthScore = (healthRef: Ref<HealthScore | null>) => {
  const score = computed(() => healthRef.value?.score ?? 0)
  const warnings = computed(() => healthRef.value?.warnings ?? [])

  const warningCount = computed(() => warnings.value.length)
  const hasWarnings = computed(() => warningCount.value > 0)

  const highestSeverity = computed(() => {
    if (!hasWarnings.value) {
      return 'LOW' as const
    }

    if (
      warnings.value.some((warningCode: string) =>
        CRITICAL_WARNING_CODES.has(warningCode)
      )
    ) {
      return 'CRITICAL' as const
    }

    if (
      warnings.value.some((warningCode: string) =>
        HIGH_WARNING_CODES.has(warningCode)
      )
    ) {
      return 'HIGH' as const
    }

    if (score.value < 70) {
      return 'MEDIUM' as const
    }

    return 'LOW' as const
  })

  const scoreBand = computed(() => {
    if (score.value >= 90) {
      return 'excellent' as const
    }

    if (score.value >= 75) {
      return 'good' as const
    }

    if (score.value >= 50) {
      return 'warning' as const
    }

    return 'critical' as const
  })

  const scoreColor = computed(() => {
    if (highestSeverity.value === 'CRITICAL' || scoreBand.value === 'critical') {
      return 'danger' as const
    }

    if (highestSeverity.value === 'HIGH' || scoreBand.value === 'warning') {
      return 'warning' as const
    }

    if (scoreBand.value === 'good') {
      return 'info' as const
    }

    return 'success' as const
  })

  const isCritical = computed(() => highestSeverity.value === 'CRITICAL')
  const isWarning = computed(
    () => highestSeverity.value === 'HIGH' || highestSeverity.value === 'MEDIUM'
  )
  const isHealthy = computed(
    () => !hasWarnings.value && score.value >= 90 && highestSeverity.value === 'LOW'
  )

  return {
    score,
    warnings,
    warningCount,
    hasWarnings,
    highestSeverity,
    scoreBand,
    scoreColor,
    isCritical,
    isWarning,
    isHealthy
  }
}
