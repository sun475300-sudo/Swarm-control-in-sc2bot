# utils package
#
# 이 디렉토리는 jarvis_features 가 쓰는 utils.openclaw_helper 만 들고 있다.
# 봇 패키지(`wicked_zerg_challenger/utils/`)도 동일한 이름의 `utils` 패키지를
# 가지고 있으며 logger / performance_profiler / kd_tree 등 봇 전용 유틸을
# 제공한다. pytest 가 PROJECT_ROOT 를 sys.path 에 prepend 하면 이쪽
# (logger.py 가 없는) stub 이 먼저 발견되어 `from utils.logger import ...`
# 가 ModuleNotFoundError 로 실패하고, EconomyManager / StrategyManager 를
# 사용하는 30+ 개 테스트가 조용히 SKIP 된다.
#
# `extend_path` 로 sys.path 위의 다른 `utils/` 디렉토리를 같은 패키지로
# 합쳐 주면 어느 쪽 디렉토리에 있는 모듈이든 `utils.<name>` 으로 접근
# 가능하다. 봇 자신의 런타임에는 영향이 없다 (`wicked_zerg_challenger/` 가
# 자기 cwd 에서 sys.path 0 번이라 자기 utils 가 먼저 잡힘).
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
