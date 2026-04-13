<template>
  <div>Swarm Damage: {{ damage }}</div>
</template>

<script>
// Phase 203: Vue
export default {
  data() {
    return { count: 10 }
  },
  computed: {
    damage() { return this.count * 5 }
  }
}
</script>
