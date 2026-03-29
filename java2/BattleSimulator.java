// P114: Java v2 - CompletableFuture AI
import java.util.*;
import java.util.concurrent.*;
import java.util.stream.*;

public class BattleSimulator {
    private List<Unit> units = new ArrayList<>();
    
    static class Unit {
        int id;
        float health;
        float damage;
        float x, y;
        
        Unit(int id, float health, float damage, float x, float y) {
            this.id = id; this.health = health;
            this.damage = damage; this.x = x; this.y = y;
        }
    }
    
    public void addUnit(Unit u) { units.add(u); }
    
    public float calculatePower() {
        return units.stream()
            .mapToDouble(u -> u.health * u.damage)
            .sum() / 100.0;
    }
    
    public Map<Integer, Float> findThreats() {
        Map<Integer, Float> threats = new HashMap<>();
        for (Unit u : units) {
            long nearby = units.stream()
                .filter(e -> e.id != u.id && distance(u, e) < 50.0)
                .count();
            threats.put(u.id, nearby * 10.0f);
        }
        return threats;
    }
    
    private double distance(Unit a, Unit b) {
        double dx = a.x - b.x;
        double dy = a.y - b.y;
        return Math.sqrt(dx*dx + dy*dy);
    }
    
    public CompletableFuture<Float> calculatePowerAsync() {
        return CompletableFuture.supplyAsync(this::calculatePower);
    }
    
    public static void main(String[] args) {
        BattleSimulator sim = new BattleSimulator();
        sim.addUnit(new Unit(1, 40, 5, 10, 10));
        System.out.println("Power: " + sim.calculatePower());
    }
}
