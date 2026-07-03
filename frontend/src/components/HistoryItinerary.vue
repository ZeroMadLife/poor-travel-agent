<script setup lang="ts">
import type { HistoryItinerary } from '../types/api'
import ItineraryCard from './ItineraryCard.vue'

defineProps<{
  item: HistoryItinerary
}>()
</script>

<template>
  <section class="history-itinerary">
    <header>
      <strong>{{ item.destination }}</strong>
      <span>约 {{ item.total_cost }} 元</span>
    </header>
    <ItineraryCard :itinerary="item.content" />
  </section>
</template>

<style scoped>
.history-itinerary {
  display: grid;
  gap: 0.5rem;
}

header {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  color: #374151;
}
</style>
