<script setup lang="ts">
import type { Itinerary } from '../types/api'

defineProps<{ itinerary: Itinerary }>()
</script>

<template>
  <div class="itinerary-card" v-if="itinerary?.days?.length">
    <div class="card-header">
      <h4>📋 {{ itinerary.destination }} 行程</h4>
      <span v-if="itinerary.weather_summary" class="weather-tag">🌤️ {{ itinerary.weather_summary }}</span>
    </div>

    <div v-for="day in itinerary.days" :key="day.date" class="day">
      <div class="day-header">
        <h5>📅 {{ day.date }}</h5>
        <span class="day-cost">当日 {{ day.total_cost }}元</span>
      </div>

      <!-- 景点 -->
      <div v-for="spot in day.spots" :key="spot.spot_id" class="spot">
        <div class="spot-img-placeholder">🖼️</div>
        <div class="spot-info">
          <div class="spot-name">
            {{ spot.name }}
            <span v-if="spot.ticket_price === 0" class="badge free">免费</span>
            <span v-else class="badge paid">{{ spot.ticket_price }}元</span>
          </div>
          <div class="spot-meta">
            <span>⏰ {{ spot.arrival_time }}-{{ spot.departure_time }}</span>
            <span v-if="spot.duration_hours">⏳ {{ spot.duration_hours }}h</span>
            <span v-if="spot.category">🏷️ {{ spot.category }}</span>
          </div>
        </div>
      </div>

      <!-- 餐饮 -->
      <div v-if="day.meals && day.meals.length" class="meals">
        <div v-for="meal in day.meals" :key="meal.name" class="meal">
          <span class="meal-icon">{{ meal.meal_type === 'breakfast' ? '🍳' : meal.meal_type === 'lunch' ? '🍚' : '🍜' }}</span>
          <span>{{ meal.name }}</span>
          <span class="meal-cost">{{ meal.estimated_cost }}元</span>
        </div>
      </div>

      <!-- 交通 -->
      <div v-if="day.transport && day.transport.length" class="transports">
        <div v-for="(t, i) in day.transport" :key="i" class="transport">
          <span class="transport-icon">{{ t.mode === 'walking' ? '🚶' : t.mode === 'driving' ? '🚗' : '🚌' }}</span>
          <span>{{ t.from_name }} → {{ t.to_name }}</span>
          <span v-if="t.distance_m" class="transport-meta">{{ (t.distance_m / 1000).toFixed(1) }}km</span>
          <span v-if="t.duration_s" class="transport-meta">{{ Math.round(t.duration_s / 60) }}min</span>
        </div>
      </div>
    </div>

    <!-- 预算 -->
    <div v-if="itinerary.budget" class="budget-bar">
      <div class="budget-row">
        <span>💰 预算</span>
        <span :class="{ over: itinerary.budget.over_budget }">
          {{ itinerary.budget.spent }} / {{ itinerary.budget.total }} 元
          <span v-if="itinerary.budget.over_budget" class="over-tag">超支</span>
          <span v-else class="ok-tag">预算内</span>
        </span>
      </div>
      <div class="budget-progress">
        <div
          class="budget-fill"
          :class="{ over: itinerary.budget.over_budget }"
          :style="{ width: Math.min(100, (itinerary.budget.spent / itinerary.budget.total) * 100) + '%' }"
        />
      </div>
    </div>

    <div class="total-row">
      <span>总花费</span>
      <span class="total-amount">{{ itinerary.total_cost }}元</span>
    </div>
  </div>
</template>

<style scoped>
.itinerary-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 1rem;
  margin: 0.5rem 0;
  background: white;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.card-header h4 {
  margin: 0;
  font-size: 1.05rem;
}
.weather-tag {
  font-size: 0.8rem;
  color: #6b7280;
  background: #f3f4f6;
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
}
.day {
  margin: 0.75rem 0;
  padding-top: 0.5rem;
  border-top: 1px solid #f3f4f6;
}
.day:first-of-type {
  border-top: 0;
}
.day-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.day-header h5 {
  margin: 0;
  font-size: 0.95rem;
  color: #374151;
}
.day-cost {
  font-size: 0.8rem;
  color: #6b7280;
}
.spot {
  display: flex;
  gap: 0.6rem;
  padding: 0.5rem 0;
  align-items: flex-start;
}
.spot-img-placeholder {
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 6px;
  background: #f3f4f6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  flex-shrink: 0;
}
.spot-info {
  flex: 1;
  min-width: 0;
}
.spot-name {
  font-weight: 500;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.badge {
  font-size: 0.7rem;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
}
.badge.free {
  background: #dcfce7;
  color: #16a34a;
}
.badge.paid {
  background: #fef3c7;
  color: #d97706;
}
.spot-meta {
  display: flex;
  gap: 0.6rem;
  font-size: 0.78rem;
  color: #9ca3af;
  margin-top: 0.2rem;
}
.meals {
  padding: 0.3rem 0 0.3rem 3.1rem;
}
.meal {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.82rem;
  color: #4b5563;
  padding: 0.15rem 0;
}
.meal-cost {
  color: #6b7280;
  font-size: 0.78rem;
}
.transports {
  padding: 0.3rem 0 0.3rem 3.1rem;
}
.transport {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  color: #9ca3af;
  padding: 0.1rem 0;
}
.transport-meta {
  background: #f3f4f6;
  padding: 0.05rem 0.3rem;
  border-radius: 3px;
}
.budget-bar {
  margin-top: 0.75rem;
  padding-top: 0.5rem;
  border-top: 1px solid #f3f4f6;
}
.budget-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.85rem;
  margin-bottom: 0.3rem;
}
.over { color: #dc2626; }
.over-tag {
  background: #fee2e2;
  color: #dc2626;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  font-size: 0.7rem;
  margin-left: 0.3rem;
}
.ok-tag {
  background: #dcfce7;
  color: #16a34a;
  padding: 0.1rem 0.35rem;
  border-radius: 3px;
  font-size: 0.7rem;
  margin-left: 0.3rem;
}
.budget-progress {
  height: 6px;
  background: #f3f4f6;
  border-radius: 3px;
  overflow: hidden;
}
.budget-fill {
  height: 100%;
  background: #2563eb;
  border-radius: 3px;
  transition: width 0.3s;
}
.budget-fill.over {
  background: #dc2626;
}
.total-row {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid #f3f4f6;
  font-size: 0.9rem;
  font-weight: 600;
}
.total-amount {
  color: #2563eb;
}
</style>
