# ������ ���� �˻� ��� ������

## ? �˻� �׸�

1. **ȣ������� ���ǵ��� ���� �޼���**
2. **pass ���� �ִ� �޼��� (�̱���)**
3. **TODO �ּ� (���� �ʿ�)**

## ? �˻� ��� ���

### 1. �ɰ��� ����: `production_resilience.py`

#### �ε����̼� ����
- **pass �� ����**: 1800�� �̻�
- **���� ��ġ**: ��ü ���Ͽ� ���� �ɰ��� �ε����̼� ����
- **�ֿ� ���� �޼���**:
  - `_safe_train` (���� 49-81): ������ ���� ����
  - `__init__` (���� 83-179): �߸��� �鿩����
  - `fix_production_bottleneck` (���� 213-726): ������ pass ��

#### ������ �޼��� (�̹� ���� �Ϸ�)
- ? `_force_emergency_production`: ���� �Ϸ� (���� 414-470)
- ? `_boost_early_game`: ���� �Ϸ� (���� 472-520)

#### ȣ��Ǵ� �޼��� ���
- `_safe_train`: ? ���ǵ� (������ �ε����̼� ����)
- `_balanced_production`: ? ���ǵ�
- `_emergency_zergling_production`: ? ���ǵ�
- `_force_emergency_production`: ? ���ǵ�
- `_boost_early_game`: ? ���ǵ�
- `_cleanup_build_reservations`: ? ���ǵ�
- `_determine_ideal_composition`: ? ���ǵ�

### 2. TODO �ּ��� �ִ� ����

#### `utils/extracted_utilities.py`
- 16���� TODO �ּ�
- ��κ� "���� ���� �ʿ�" �ּ�

#### `unit_factory.py`
- 20�� �̻��� TODO �ּ�
- "�ߺ� �ڵ� ���� - ���� �Լ��� ���� ����"

#### `tools/improved_compare_pro_vs_training.py`
- "���� ���÷��� �Ľ� ����" �ʿ�
- "���� �� ������Ʈ ���� ����" �ʿ�

### 3. pass ���� ���� ����

1. **`production_resilience.py`**: 1800�� �̻� ?? **�ɰ�**
2. **`unit_factory.py`**: ���� ��
3. **`utils/common_utilities.py`**: ���� ��
4. **`utils/extracted_utilities.py`**: ���� ��

## ? �켱������ ���� �ʿ� ����

### ? �ֿ켱 (��� ���� �ʿ�)

1. **`production_resilience.py` ��ü �籸��**
   - �ε����̼� ���� ����
   - pass �� ���� �� ���� ���� ����
   - `_safe_train` �޼��� ���� ���ۼ�
   - `__init__` �޼��� ���� ����

### ? ���� �켱����

2. **`unit_factory.py` �ߺ� �ڵ� �����丵**
   - ���� �Լ� ����
   - pass �� ����

3. **`utils/extracted_utilities.py` ���� �Ϸ�**
   - TODO �ּ� ����
   - ���� ���� ����

### ? �߰� �켱����

4. **`tools/improved_compare_pro_vs_training.py`**
   - ���÷��� �Ľ� ����
   - �� ������Ʈ ���� ����

5. **`utils/common_utilities.py`**
   - pass �� ����
   - �̱��� �޼��� ����

## ? �� �м�

### `production_resilience.py` ���� ����

```python
async def _safe_train(self, unit, unit_type):
    """Safely train a unit, handling both sync and async train() methods"""
    try:
    pass  # ? �߸��� �ε����̼�

    except Exception:
        pass
        pass  # ? �ߺ� pass
    pass  # ? �߸��� ��ġ

    except Exception:  # ? try ���� ���� except
        pass
        result = unit.train(unit_type)  # ? �߸��� �鿩����
```

**�ùٸ� ����:**
```python
async def _safe_train(self, unit, unit_type):
    """Safely train a unit, handling both sync and async train() methods"""
    try:
        result = unit.train(unit_type)
        # train() may return bool or coroutine
        if hasattr(result, '__await__'):
            await result
        return True
    except Exception as e:
        current_iteration = getattr(self.bot, "iteration", 0)
        if current_iteration % 200 == 0:
            print(f"[WARNING] _safe_train error: {e}")
        return False
```

## ? �Ϸ�� �۾�

1. ? `_force_emergency_production` �޼��� ����
2. ? `_boost_early_game` �޼��� ����
3. ? ������ ���� �˻� ���� ���� (`tools/check_missing_logic.py`)

## ? ���� �ܰ�

1. **`production_resilience.py` ��ü �籸��** (�ֿ켱)
2. **�ε����̼� ���� �ϰ� ����**
3. **pass �� ���� �� ���� ���� ����**
4. **TODO �ּ� ó��**

## ? ����

- ��� �޼��� ȣ���� ���ǵǾ� ���� (�ε����̼� ������ ����)
- �ֿ� ������ �ڵ� ������ �ƴ� �ε����̼� ����
- `production_resilience.py`�� ���� �ɰ��� ���� ����
