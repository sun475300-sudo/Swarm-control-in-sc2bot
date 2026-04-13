// Phase 212: Lit
import { LitElement, html } from 'lit';

class BattleSim extends LitElement {
  render() {
    return html`<div>Battle Simulation</div>`;
  }
}

customElements.define('battle-sim', BattleSim);
