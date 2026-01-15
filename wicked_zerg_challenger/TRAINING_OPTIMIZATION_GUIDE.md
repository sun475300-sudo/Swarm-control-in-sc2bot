# �Ʒ� ����ȭ ���̵�

## ����

�Ʒÿ� �ʿ��� �ٽ� ���ϸ� ����� ���ʿ��� ���ϵ��� �����Ͽ� ������Ʈ�� ����ȭ�մϴ�.

## ���� ���

### 1. ��� ���� (.bak)

- ��� `.bak` ���� (73��)

- ��: `wicked_zerg_bot_pro.py.bak`, `config.py.bak` ��

### 2. ���� ���� (.md)

- ����Ʈ �� �м� ���� (��κ�)

- ������ ����:
  - `README.md`, `README_BOT.md`, `README_ko.md`, `README_�ѱ���.md`
  - `SETUP_GUIDE.md`
  - `local_training/������/FILE_STRUCTURE.md`

### 3. ���ʿ��� ���丮

- `backup_before_refactoring/` - �����丵 ���

- `monitoring/` - ����͸� �ý��� (�Ʒÿ��� ���ʿ�)

- `static/` - ���� ����

- `services/` - ���� ����

### 4. tools ���� ����

- �Ʒÿ� �ʿ��� ���ϸ� ����:
  - `integrated_pipeline.py`
  - `hybrid_learning.py`

- ������ ���� ���ϵ��� ����

## ������ �ʼ� ����

### �ٽ� ���� ����

- `run.py`

- `run_with_training.py`
- `wicked_zerg_bot_pro.py`

- `zerg_net.py`
- `config.py`

- `requirements.txt`

### �Ŵ��� ����

- `combat_manager.py`

- `economy_manager.py`
- `production_manager.py`

- `intel_manager.py`
- `scouting_system.py`

- `queen_manager.py`
- `micro_controller.py`

- `telemetry_logger.py`
- `rogue_tactics_manager.py`

- `unit_factory.py`
- `spell_unit_manager.py`

- `map_manager.py`

### �ʼ� ���丮

- `combat/`

- `core/`
- `sc2_env/`

- `utils/`
- `config/`

- `local_training/`
- `models/`

- `data/`
- `bat/`

## ���� ���

### 1. ����Ʈ ���� (����)

```bash

python tools\optimize_for_training.py --report-only

```

### 2. ���� ����ȭ ����

```bash

python tools\optimize_for_training.py --execute

```

�Ǵ� ��ġ ���� ���:

```bash

bat\optimize_for_training.bat

```bash

## ���ǻ���

1. **��� �ʼ�**: ����ȭ ���� ������Ʈ ��ü�� ����ϼ���.
2. **������ ����**: ���� ����Ʈ�� Ȯ���� �� �����ϼ���.
3. **Git Ŀ��**: ����ȭ ���� ���� ���¸� Ŀ���ϼ���.

## ���� ȿ��

- ���ŵ� ����: �� 300�� �̻�

- ����� ����: ���� MB ~ ���� MB
- ������Ʈ ũ��: �� 50-70% ����

## ���� ���

Git�� ����ϴ� ���:

```bash

git checkout HEAD -- .

```

�Ǵ� ������� ����:

```bash

# ��� �������� �ʿ��� ���� ����

```

