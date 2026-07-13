<script setup lang="ts">
defineProps<{
  phase: string
}>()
</script>

<template>
  <div class="thinking-indicator" role="status" aria-live="polite">
    <span class="thinking-sheen" aria-hidden="true"></span>
    <span class="thinking-dots" aria-hidden="true">
      <span class="dot"></span>
      <span class="dot"></span>
      <span class="dot"></span>
    </span>
    <span class="thinking-copy"><strong>思考中</strong><span class="thinking-phase">{{ phase }}</span></span>
  </div>
</template>

<style scoped>
.thinking-indicator {
  display: flex;
  position: relative;
  overflow: hidden;
  width: fit-content;
  align-items: center;
  gap: 8px;
  max-width: 100%;
  margin: 0 0 12px;
  padding: 8px 14px;
  border: 1px solid var(--sage-border);
  border-radius: var(--sage-radius-lg);
  background: linear-gradient(100deg, var(--sage-surface-raised) 25%, color-mix(in srgb, var(--sage-success-bg) 72%, var(--sage-surface-raised)) 50%, var(--sage-surface-raised) 75%);
  background-size: 220% 100%;
  font-size: 13px;
  color: var(--sage-text-secondary);
}

.thinking-indicator { animation: thinking-sheen 2.2s ease-in-out infinite; }
.thinking-sheen { position:absolute; inset:0; pointer-events:none; background:linear-gradient(90deg, transparent, rgb(255 255 255 / 14%), transparent); transform:translateX(-100%); animation:thinking-sweep 1.9s ease-in-out infinite; }
.thinking-copy { display:flex; align-items:baseline; gap:8px; min-width:0; }
.thinking-copy strong { color:var(--sage-text); font-size:12px; }

.thinking-dots {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  flex-shrink: 0;
}

.thinking-dots .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--sage-text-secondary);
  opacity: 0.4;
  animation: thinking-pulse 1.2s ease-in-out infinite;
}

.thinking-dots .dot:nth-child(2) {
  animation-delay: 0.2s;
}

.thinking-dots .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes thinking-pulse {
  0%,
  80%,
  100% {
    opacity: 0.3;
    transform: scale(0.8);
  }
  40% {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes thinking-sheen { 0%,100% { background-position: 100% 0; } 50% { background-position: 0 0; } }
@keyframes thinking-sweep { 0% { transform:translateX(-100%); } 55%,100% { transform:translateX(100%); } }

.thinking-phase {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (prefers-reduced-motion: reduce) {
  .thinking-indicator, .thinking-sheen, .thinking-dots .dot { animation: none; }
}

</style>
