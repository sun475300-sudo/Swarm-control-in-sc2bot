<script>
// Phase 202: Svelte
let count = 10;
$: damage = count * 5;
</script>

<h1>Swarm Damage: {damage}</h1>
