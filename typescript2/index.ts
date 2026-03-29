// P116: TypeScript v2 - Async Game State Management
interface Unit {
    id: number;
    health: number;
    damage: number;
    x: number;
    y: number;
}

class BattleSimulator {
    private units: Unit[] = [];
    
    addUnit(unit: Unit): void {
        this.units.push(unit);
    }
    
    calculatePower(): number {
        const power = this.units.reduce((sum, u) => sum + u.health * u.damage, 0);
        return power / 100;
    }
    
    findThreats(): Map<number, number> {
        const threats = new Map<number, number>();
        for (const u of this.units) {
            const nearby = this.units.filter(e => 
                e.id !== u.id && this.distance(u, e) < 50
            ).length;
            threats.set(u.id, nearby * 10);
        }
        return threats;
    }
    
    private distance(a: Unit, b: Unit): number {
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        return Math.sqrt(dx * dx + dy * dy);
    }
    
    async analyzeAsync(): Promise<{power: number, threats: Map<number, number>}> {
        return Promise.resolve({
            power: this.calculatePower(),
            threats: this.findThreats()
        });
    }
}

const sim = new BattleSimulator();
sim.addUnit({id: 1, health: 40, damage: 5, x: 10, y: 10});
console.log("Power:", sim.calculatePower());
