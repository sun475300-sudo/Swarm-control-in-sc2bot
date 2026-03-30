// Wicked Zerg - Battle Simulation
// Phase 137: Processing (Java)

class BattleUnit {
  int unitType;
  float health;
  float damage;
  float armor;
  PVector position;
  
  BattleUnit(int t, float h, float d, float a, float x, float y) {
    unitType = t;
    health = h;
    damage = d;
    armor = a;
    position = new PVector(x, y);
  }
  
  float getStrength() {
    float effective = damage * health / 100;
    return effective * (1 - armor * 0.01);
  }
}

int calculateSwarmDamage(int count) {
  return count * 5;
}

ArrayList<PVector> swarmFormation(float centerX, float centerY, int count, float radius) {
  ArrayList<PVector> positions = new ArrayList<PVector>();
  for (int i = 0; i < count; i++) {
    float angle = TWO_PI * i / count;
    float x = centerX + radius * cos(angle);
    float y = centerY + radius * sin(angle);
    positions.add(new PVector(x, y));
  }
  return positions;
}

float unitStrength(float health, float damage, float armor) {
  float effective = damage * health / 100;
  return effective * (1 - armor * 0.01);
}

boolean battleOutcome(ArrayList<BattleUnit> attackers, ArrayList<BattleUnit> defenders) {
  float attackPower = 0;
  float defensePower = 0;
  for (BattleUnit u : attackers) attackPower += u.getStrength();
  for (BattleUnit u : defenders) defensePower += u.getStrength();
  return attackPower > defensePower;
}

void setup() {
  println("Battle Simulation Initialized - Processing");
}
