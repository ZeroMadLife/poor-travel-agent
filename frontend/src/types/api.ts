export type ProgressEvent = {
  type: 'progress'
  agent: string
  message: string
}

export type ToolCallEvent = {
  type: 'tool_call'
  tool: string
  args: Record<string, unknown>
}

export type VerificationIssue = {
  code: string
  message: string
  severity: string
}

export type VerificationResult = {
  passed: boolean
  issues: VerificationIssue[]
}

export type BudgetBreakdown = {
  total: number
  spent: number
  transport?: number
  accommodation?: number
  food?: number
  tickets?: number
  misc?: number
  over_budget: boolean
}

export type SpotVisit = {
  spot_id: string
  name: string
  arrival_time: string
  departure_time: string
  duration_hours?: number
  ticket_price: number
  category?: string
  location?: string
}

export type Meal = {
  name: string
  meal_type: string
  estimated_cost: number
}

export type Transport = {
  from_name: string
  to_name: string
  mode: string
  distance_m: number
  duration_s: number
}

export type ItineraryDay = {
  date: string
  spots: SpotVisit[]
  meals?: Meal[]
  transport?: Transport[]
  total_cost: number
}

export type Itinerary = {
  destination: string
  days: ItineraryDay[]
  total_cost: number
  weather_summary?: string
  budget?: BudgetBreakdown | null
}

export type ResultEvent = {
  type: 'result'
  itinerary: Itinerary
  validation: VerificationResult
  metrics: Record<string, unknown>
}

export type ErrorEvent = {
  type: 'error'
  message: string
  recoverable: boolean
}

export type ServerEvent = ProgressEvent | ToolCallEvent | ResultEvent | ErrorEvent

export type ChatStartResponse = {
  session_id: string
}
