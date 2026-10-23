export interface PlanUpgradeDetails {
  feature?: string
  required_plan?: string
  [key: string]: unknown
}

export type PlanUpgradeListener = (details: PlanUpgradeDetails) => void

const planUpgradeListeners = new Set<PlanUpgradeListener>()

export function emitPlanUpgradeRequired(details: PlanUpgradeDetails): void {
  for (const listener of [...planUpgradeListeners]) {
    listener(details)
  }
}

export function onPlanUpgradeRequired(listener: PlanUpgradeListener): () => void {
  planUpgradeListeners.add(listener)
  return () => {
    planUpgradeListeners.delete(listener)
  }
}
