// Phase 210: SolidJS
import { createSignal } from "solid-js";

function App() {
  const [count, setCount] = createSignal(10);
  return <h1>Damage: {count() * 5}</h1>;
}

export default App;
