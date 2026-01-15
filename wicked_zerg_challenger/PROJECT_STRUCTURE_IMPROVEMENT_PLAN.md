# ������Ʈ ���� ���� �� ��üȭ ��ȹ

**�ۼ� �Ͻ�**: 2026-01-15  
**����**: ? **���� ��**

---

## ? ���� ��� ���

### ? �̹� ������ �κ�

1. **micro_controller.py** - Potential Field & Boids �˰����� ?
   - Potential Field Method ���� �Ϸ�
   - Boids Algorithm ���� �Ϸ�
   - Swarm Formation Control ���� �Ϸ�
   - **���� �ʿ�**: `@dataclass` import �߰�, SC2 Point2 import ����

2. **zerg_net.py** - �Ű�� ���� ?
   - 15���� �Է� ���� ���� (Self 5 + Enemy 10)
   - 4���� ��� (Attack/Defense/Economy/Tech)

### ?? ���� �ʿ� ����

1. **���� ���� ��Ī ����**
   - `_collect_state()` �Լ��� `zerg_net.py` �Է� ���� ��ġ Ȯ��
   - StateEncoder�� ���� ������ ���� ���� ����

2. **�ϵ��ڵ��� ��� ����**
   - `D:\replays\replays` �� `config.py`�� �̵�
   - ȯ�� ���� ���� �߰�

3. **������Ʈ ���� �籸��**
   - `local_training/` �� `src/bot/` ����ȭ
   - GitHub ����� ��üȭ

4. **requirements.txt ����**
   - �ʼ� ���̺귯���� ����
   - ���� �浹 �ذ�

---

## ? �켱������ �׼� �÷�

### [1����] �ٽ� ���� ���� �� ����

#### 1.1 micro_controller.py ����

- ? `@dataclass` import �߰�

- ? SC2 Point2 import ����
- ? �ڵ� �ϼ��� Ȯ��

#### 1.2 ���� ���� ��Ī ����

- `wicked_zerg_bot_pro.py`�� `_collect_state()` �Լ� Ȯ��

- 15���� ���� ���� Ȯ��:
  - Self (5): Minerals, Gas, Supply Used, Drone Count, Army Count
  - Enemy (10): Army Count, Tech Level, Threat Level, Unit Diversity, Scout Coverage, Main Distance, Expansion Count, Resource Estimate, Upgrade Count, Air/Ground Ratio

- `zerg_net.py`�� `input_size=15` Ȯ��

#### 1.3 �Ŵ��� �������̽� �ϰ���

- `wicked_zerg_bot_pro.py`�� �� �Ŵ��� �� ������ ��ȯ ��� ����

- �������̽� ����ȭ

---

### [2����] ���� ��� ���� (�̹� �Ϸ�!)

**micro_controller.py�� �̹� ������:**

- ? Potential Field �˰�����

- ? Boids �˰����� (Separation, Alignment, Cohesion)
- ? Swarm Formation Control (Circle, Line, Wedge)

- ? Obstacle Avoidance
- ? Cluster Detection (Baneling vs Marines)

**�߰� ���� ����:**

- ���� SC2 ���ӿ��� ���Ǵ��� Ȯ��

- ���� ����ȭ

---

### [3����] �ϵ��ڵ� ��� ����

#### 3.1 config.py�� ��� ���� �߰�

```python

# Replay paths

REPLAY_DIR = Path(os.environ.get("REPLAY_DIR", "D:/replays"))
REPLAY_SOURCE_DIR = Path(os.environ.get("REPLAY_SOURCE_DIR", REPLAY_DIR / "replays"))
REPLAY_COMPLETED_DIR = REPLAY_SOURCE_DIR / "completed"

```

#### 3.2 integrated_pipeline.py ����

- �ϵ��ڵ��� `D:\replays\replays` ����

- `config.py`���� ��� �ε�

---

### [4����] ������Ʈ ���� �籸��

#### 4.1 ���丮 ���� ����

```

wicked_zerg_challenger/
������ src/
��   ������ bot/
��   ��   ������ __init__.py
��   ��   ������ wicked_zerg_bot_pro.py
��   ��   ������ zerg_net.py
��   ��   ������ micro_controller.py
��   ������ managers/
��   ��   ������ combat_manager.py
��   ��   ������ production_manager.py
��   ��   ������ ...
��   ������ training/
��       ������ local_training/
��       ������ ...
������ config.py
������ requirements.txt
������ ...

```

#### 4.2 GitHub ����� ��üȭ

- ���� �۵��ϴ� �ڵ� ���ϵ��� ������ ��ġ�� �̵�

- �� `__init__.py` ���ϵ鿡 ���� �ڵ� �߰�
- ���� ������ ���� �߰� (`telemetry_0.csv` ��)

---

### [5����] requirements.txt ����

#### 5.1 �ʼ� ���̺귯���� ����

- burnysc2 (SC2 API)

- torch (�Ű��)
- numpy (��ġ ����)

- loguru (�α�)
- sc2reader (���÷��� �м�)

- google-generativeai (Self-Healing)
- flask, fastapi (��ú���)

#### 5.2 ���� �浹 �ذ�

- numpy ���� ȣȯ�� Ȯ��

- loguru ���� ȣȯ�� Ȯ��

---

## ? �۾� üũ����Ʈ

### ��� �۾�

- [ ] micro_controller.py import ����

- [ ] _collect_state() �Լ� Ȯ�� �� ����
- [ ] config.py�� ��� ���� �߰�

- [ ] �ϵ��ڵ��� ��� ����

### �ܱ� �۾�

- [ ] ������Ʈ ���� �籸��

- [ ] requirements.txt ����
- [ ] �Ŵ��� �������̽� ����ȭ

### �߱� �۾�

- [ ] GitHub ����� ���� ����

- [ ] ���� ������ �߰�
- [ ] �׽�Ʈ �ڵ� �ۼ�

---

**�ۼ���**: AI Assistant  
**���� ������Ʈ**: 2026-01-15

