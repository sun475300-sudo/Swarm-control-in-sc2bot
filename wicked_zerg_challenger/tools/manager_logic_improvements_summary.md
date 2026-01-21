# �Ŵ��� ���� ���� �Ϸ� ������

**���� �Ͻ�**: 2026-01-15  
**���� �׸�**: QueenManager, SpellUnitManager, EconomyCombatBalancer

---

## ���� �Ϸ� ����

### ? 1. QueenManager ���� (�Ϸ�)

**������**:
- ���� ���� ���ǿ� `gas_threshold = 100` ���� ���� (������ ������ �Ҹ����� ����)
- �ڵ� �� "STYLE" �ּ� ��ġ
- ��� ���� ȿ���� ���� (������ �ʹ� �ָ��� �ɾ�� ����)

**�ذ�**:
- **���� ���� ����**: ���� ���� �� ���� üũ ���� ����
- **�ڵ� ����**: STYLE �ּ� ���� �� �ڵ� ������ ����
- **��� ���� ȿ���� ����**: �Ÿ� üũ ��ȭ (20 -> 10), ���� �̵� �Ÿ� ���� �߰�

**���� ����**:
- `wicked_zerg_challenger/queen_manager_improvements.py` - ������ ���� ������

**�ֿ� ���� ����**:
- `produce_queen()`: ���� ���� ���� ����
- `manage_larva_inject()`: �Ÿ� üũ ��ȭ, ���� ���Ҵ� ���� �߰�
- `max_queen_travel_distance`: ���� �̵� �ִ� �Ÿ� ���� (10.0)

---

### ? 2. SpellUnitManager ���� (�Ϸ�)

**������**:
- �ߺ� �ڵ� �ּ� �� �̿ϼ� �κ�
- �Ű� ����� Ÿ�� ������ (4������)
- ������ ���� �� ���� ���� ����

**�ذ�**:
- **�ߺ� �ڵ� ����**: `_find_nearby_targets()` ���� �Լ� ����
- **�Ű� ����� Ÿ�� Ȯ��**: ���� ���, ����, ��������, �Ҹ��� �߰�
- **������ ���� �߰�**: ������ 50 �̸� �� �����ϰ� ����, ���� Consume ���� �߰�

**���� ����**:
- `wicked_zerg_challenger/spell_unit_manager.py` - ���� ���� ������ ����

**�ֿ� ���� ����**:
- `_find_nearby_targets()`: ���� Ÿ���� �Լ� ���� (�ߺ� �ڵ� ����)
- `_update_infestors()`: �Ű� ����� Ÿ�� Ȯ�� (8����)
- `_retreat_low_energy_unit()`: ������ ���� �� ���� ���� �߰�
- ���� Consume �ɷ� Ȱ�� (�Ʊ� �ǹ����� ������ ����)

---

### ? 3. EconomyCombatBalancer ���� (�Ϸ�)

**������**:
- Ȯ�� ��� ������ �Ҿ����� (`random.random() < threshold`)
- �������� ���� ��ǥ ��ġ (6�� ���� ��� 30��)
- �ϵ��ڵ��� ���� Ÿ�� ���

**�ذ�**:
- **�������� ���� ����**: Ȯ�� ��� ���� ���� ���� üũ
- **��� ��ǥ ����**: �ʹ� 30��, �߹� 60��, �Ĺ� 80��
- **���� ���� Ÿ�� ����**: �ϵ��ڵ� ����, `unit.is_army` �Ǵ� ���� ����

**���� ����**:
- `wicked_zerg_challenger/local_training/economy_combat_balancer_improved.py` - ������ ����-���� ���� �����

**�ֿ� ���� ����**:
- `should_make_drone()`: �������� ���� ���� (Ȯ�� ��� ���� ���� üũ)
- `_calculate_target_drones()`: ��� ��ǥ ���� ���� (60-80��)
- `count_army_units()`: ���� ���� Ÿ�� ���� (�ϵ��ڵ� ����)
- `production_history`: ���� ���� ���� (�������� ����)

---

## ���� ȿ��

### QueenManager
- ? �ʹ� ���忡�� ���� ���� ����ȭ (���� ���� ����)
- ? ��� ���� ȿ�� ��� (�Ÿ� üũ ��ȭ)
- ? �ڵ� ������ ���� (STYLE �ּ� ����)

### SpellUnitManager
- ? �ڵ� �ߺ� ���� (���� �Լ� ����)
- ? ���� ȿ�� ��� (�Ű� ����� Ÿ�� Ȯ��)
- ? ���� ���� ������ ��� (������ ���� �� ����)

### EconomyCombatBalancer
- ? ���� ���� ����ȭ (�������� ����)
- ? �Ĺ� �ڿ��� Ȯ�� (��� ��ǥ ����)
- ? ������ ���� Ÿ�� ���� (�ϵ��ڵ� ����)

---

## ���� ���

### 1. QueenManager ����
```python
# bot_step_integration.py �Ǵ� ���� �� ���Ͽ���
from queen_manager_improvements import QueenManagerImproved

if self.bot.queen_manager is None:
    self.bot.queen_manager = QueenManagerImproved(self.bot)
```

### 2. SpellUnitManager ����
- ���� `spell_unit_manager.py` ������ �̹� �����Ǿ����Ƿ� �ڵ� �����
- `bot_step_integration.py`���� `SpellUnitManager` import Ȯ��

### 3. EconomyCombatBalancer ����
```python
# production_resilience.py �Ǵ� ���� �� ���Ͽ���
from local_training.economy_combat_balancer_improved import EconomyCombatBalancerImproved

if self.bot.economy_balancer is None:
    self.bot.economy_balancer = EconomyCombatBalancerImproved(self.bot)
```

---

## ���� �ܰ�

1. **���� �׽�Ʈ**: ���� ������ �Ŵ������� ���� ���ӿ��� ���� �۵��ϴ��� Ȯ��
2. **�Ķ���� Ʃ��**: ��� ��ǥ ��ġ, ���� �̵� �Ÿ� �� ���� ���� �����ͷ� ����
3. **���� ����͸�**: ���� ������ ������ ���� ��� �⿩�ϴ��� ����

---

**��� ���� ������ �Ϸ�Ǿ����ϴ�!** ?
