# ���� ���� ���

## ? �Ϸ�� ���� ����

### 1. �� ���� ���� ����
**����**: `unit_factory.py`, `queen_manager.py`
- **���� ����**: `_produce_queen` �޼��忡�� `gas_threshold` üũ ����
- **����**: ������ �����ص� �� ������ �����ϵ��� ����
- **���� ��ġ**:
  - `unit_factory.py` ���� 1011, 1014
  - `queen_manager.py` ���� 85, 88

**���� ��**:
```python
gas_threshold = 100
if b.minerals < mineral_threshold or b.vespene < gas_threshold:
    return
```

**���� ��**:
```python
# gas_threshold removed per user request
if b.minerals < mineral_threshold:
    return
```

### 2. �ڿ� �÷��� ��� �߰�
**����**: `unit_factory.py`, `production_resilience.py`
- **���� ����**: �̳׶��� 1000 �̻��� ��� �ֹ��� ���� ������ �ǳʶٰ� ��� �ֹ����� ���۸����� ����
- **����**: �ڿ� ���� ���� �� ��� ���� ����
- **���� ��ġ**:
  - `unit_factory.py` ���� 107-160: �ֹ��� ���� ������ �÷��� ��� �߰�
  - `production_resilience.py` ���� 298-330: `_balanced_production`�� �÷��� ��� �߰�
  - `production_resilience.py` ���� 390-420: `_emergency_zergling_production`�� �÷��� ��� �߰�

**�߰��� ����**:
```python
# RESOURCE FLUSH MODE: When minerals >= 1000, skip reservation and use all larvae
if b.minerals >= 1000:
    # Flush mode: Use all available larvae, no reservation
    available_larvae = larvae
    reserved_larvae_count = 0
```

### 3. �뱺�� ���� �켱���� ����
**����**: `production_resilience.py`
- **���� ����**: `supply_left < 4`���� `supply_left < 6`���� �����Ͽ� �� ���� ����
- **����**: ����ǰ ���� ���� �̸� �����Ͽ� ���� Ȯ��
- **���� ��ġ**: `production_resilience.py` ���� 614-628

**���� ��**:
```python
if b.supply_left < 4 and b.supply_cap < 200:
```

**���� ��**:
```python
# IMPROVED: Overlord production priority - produce before supply_left < 4
# Changed from < 4 to < 6 to ensure we have supply buffer before running out
if b.supply_left < 6 and b.supply_cap < 200:
```

## ? ���� ȿ��

### 1. �� ���� ����
- ������ �����ص� �� ���� ����
- �ʹ� ��� ���� �� ũ�� Ȯ�� ����

### 2. �ڿ� �÷��� ���
- �̳׶� 1000+ �� ��� ���۸� ����
- �ڿ� ���� ����
- �ֹ��� ���� ���� ��ȸ�� ���� ����

### 3. �뱺�� ���� ����
- `supply_left < 6`���� ���� ����
- ����ǰ ���� ���� �̸� ����
- ���� ���� ����

## ? �߰� Ȯ�� ����

1. **�ٸ� �뱺�� ���� ��ġ**: `production_resilience.py` ���� 1033�� `supply_left < 5` üũ�� ���� (�߰� ���� ����)

2. **�ڿ� �÷��� ��� �Ӱ谪**: ���� 1000 �̳׶��� ���� (�ʿ�� ���� ����)

3. **�ֹ��� ���� ����**: `unit_factory.py`���� �÷��� ��� �߰� �Ϸ�

## ? ���� ����

- ��� ���� ������ ���� ������ ȣȯ�ǵ��� �����
- �÷��� ���� �ڿ��� �����ϰ� ������ ���� Ȱ��ȭ
- �뱺�� ������ ����ǰ ������ ���� �� �̸� �����Ͽ� ���� ����
