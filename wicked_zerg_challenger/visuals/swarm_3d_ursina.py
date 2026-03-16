# ============================================================
# Swarm-Net 3D Simulator — Ursina Engine (v12.0)
# ============================================================
# 실행: python swarm_3d_ursina.py
# 필수: pip install ursina
#
# 조작:
#   마우스 우클릭 드래그 — 회전 / 마우스 휠 — 줌
#   Space — 드론 추가  |  X — 드론 퇴거
#   M — 메시 라인 토글  |  R — 리셋
#   1/2/3 — 카메라 프리셋
# ============================================================

import math
import random
from ursina import *

app = Ursina(
    title='Swarm-Net Airspace Control',
    borderless=False,
    fullscreen=False,
    development_mode=False,
    size=(1400, 800),
)

# ================================================================
# ★ DARK MODE — 조명 완전 제거, unlit 엔티티만 자체 발광
# ================================================================
window.color = color.black

# Sky 파괴
for entity in scene.entities[:]:
    if type(entity).__name__ == 'Sky':
        destroy(entity)

# ★ 조명 없음 — 모든 엔티티가 unlit=True 로 자체 발광

# ================================================================
# CONFIG
# ================================================================
NUM_SWARM = 6
INITIAL_USER = 4
HEX_RADIUS = 10.0
HEX_HEIGHT = 6.0
TIMER_MAX = 45.0
TIMER_WARN = 15.0
TIMER_EVICT = 8.0

camera.clip_plane_far = 500
editor_cam = EditorCamera(rotation_smoothing=8, zoom_speed=2)

# ================================================================
# COLOR PALETTE
# ================================================================
C_CYAN = color.cyan
C_CYAN_DIM = color.rgb(0, 40, 70)
C_GREEN = color.green
C_ORANGE = color.orange
C_RED = color.red
C_MAGENTA = color.rgb(255, 0, 160)
C_WHITE = color.white
C_HUD_TITLE = color.rgb(0, 255, 210)

# ================================================================
# GROUND — plane 제거, 검은 빈 공간 + 부유 그리드
# ================================================================
# ★ 바닥 plane 없음 → window.color=black이 배경

# 부유 그리드 — 검은 배경 위에서 잘 보이는 어두운 시안
for i in range(-20, 21, 5):
    Entity(model='cube', scale=(0.02, 0.005, 50),
           position=(i, 0, 0),
           color=color.rgb(0, 60, 90), alpha=0.15, unlit=True)
    Entity(model='cube', scale=(50, 0.005, 0.02),
           position=(0, 0, i),
           color=color.rgb(0, 60, 90), alpha=0.15, unlit=True)

# 나침반
for lbl, pos, c in [
    ('N', Vec3(0, 0.03, 12), color.rgb(200, 50, 50)),
    ('S', Vec3(0, 0.03, -12), color.rgb(60, 60, 80)),
    ('E', Vec3(12, 0.03, 0), color.rgb(60, 60, 80)),
    ('W', Vec3(-12, 0.03, 0), color.rgb(60, 60, 80)),
]:
    Text(text=lbl, scale=5, color=c, position=pos,
         billboard=True, origin=(0, 0), background=False)

# ================================================================
# GCS (Ground Control Station)
# ================================================================
Entity(model='cube', scale=(1.2, 0.15, 1.2),
       color=color.rgb(0, 30, 50), position=(0, 0.08, 0), unlit=True)
Entity(model='cube', scale=(0.3, 1.8, 0.3),
       color=color.rgb(0, 45, 70), position=(0, 0.9, 0), unlit=True)
gcs_dish = Entity(
    model='sphere', scale=(0.5, 0.2, 0.5),
    color=C_CYAN_DIM, alpha=0.5, position=(0, 1.9, 0), unlit=True,
)
Text(text='GCS', scale=5, color=C_CYAN,
     position=Vec3(0, 2.5, 0), billboard=True, origin=(0, 0),
     background=False)

# ================================================================
# SENTINEL DRONES (군집 드론) — unlit=True 자체 발광, 네온 시안
# ================================================================
swarm_positions = []
swarm_drones = []

for i in range(NUM_SWARM):
    angle = math.radians(60 * i + 30)
    x = HEX_RADIUS * math.cos(angle)
    z = HEX_RADIUS * math.sin(angle)
    pos = Vec3(x, HEX_HEIGHT, z)
    swarm_positions.append(pos)

    # ★ unlit=True — 조명과 무관하게 시안색 자체 발광
    drone = Entity(
        model='diamond', scale=(0.7, 1.0, 0.7),
        color=C_CYAN, position=pos, unlit=True,
    )
    swarm_drones.append(drone)

    Text(
        text=f'S{i + 1}', scale=5,
        color=C_CYAN,
        position=pos + Vec3(0, 1.6, 0),
        billboard=True, origin=(0, 0),
        background=False,
    )

    # 바닥 투영
    Entity(
        model='circle', scale=0.7,
        color=C_CYAN, alpha=0.08,
        position=Vec3(x, 0.02, z), rotation_x=90, unlit=True,
    )

    # 수직선
    Entity(
        model='cube', scale=(0.015, HEX_HEIGHT, 0.015),
        position=Vec3(x, HEX_HEIGHT / 2, z),
        color=C_CYAN_DIM, alpha=0.10, unlit=True,
    )

# ================================================================
# MESH LINES (결계선) — unlit=True, 충분한 두께
# ================================================================
mesh_lines = []
mesh_visible = True

# 외곽 결계선 — 두꺼운 시안
for i in range(NUM_SWARM):
    j = (i + 1) % NUM_SWARM
    p1, p2 = swarm_positions[i], swarm_positions[j]
    mid = (p1 + p2) / 2
    dist = (p2 - p1).length()
    ay = math.degrees(math.atan2(p2.x - p1.x, p2.z - p1.z))
    mesh_lines.append(Entity(
        model='cube', scale=(0.06, 0.06, dist),
        position=mid, color=C_CYAN, alpha=0.4,
        rotation_y=ay, unlit=True,
    ))

# 대각선 결계선
for i in range(NUM_SWARM):
    opp = (i + 3) % NUM_SWARM
    p1, p2 = swarm_positions[i], swarm_positions[opp]
    mid = (p1 + p2) / 2
    dist = (p2 - p1).length()
    ay = math.degrees(math.atan2(p2.x - p1.x, p2.z - p1.z))
    mesh_lines.append(Entity(
        model='cube', scale=(0.025, 0.025, dist),
        position=mid, color=color.rgb(0, 50, 100), alpha=0.10,
        rotation_y=ay, unlit=True,
    ))

# ================================================================
# RADAR RING — 바닥 펄스, unlit=True
# ================================================================
class RadarRing(Entity):
    def __init__(self, phase=0.0):
        super().__init__(
            model='circle', scale=0.5,
            color=color.rgb(0, 200, 150), alpha=0.10,
            position=(0, 0.03, 0), rotation_x=90, unlit=True,
        )
        self._speed = 4.5
        self.scale_x += phase
        self.scale_z = self.scale_x
        self.alpha = max(0, 0.10 - phase * 0.01)

    def update(self):
        self.scale_x += self._speed * time.dt
        self.scale_z = self.scale_x
        self.alpha -= 0.04 * time.dt
        if self.alpha <= 0 or self.scale_x > HEX_RADIUS * 3:
            self.scale_x = 0.5
            self.scale_z = 0.5
            self.alpha = 0.10

radar_rings = [RadarRing(phase=i * 3.5) for i in range(2)]

# ================================================================
# USER DRONES — unlit=True 자체 발광, 빌보드 라벨
# ================================================================
STATE_AUTHORIZED = 'AUTHORIZED'
STATE_WARNING = 'WARNING'
STATE_EXPIRED = 'EXPIRED'
STATE_EVICTING = 'EVICTING'


class UserDrone:
    _counter = 0

    def __init__(self):
        UserDrone._counter += 1
        self.idx = UserDrone._counter
        self.timer = TIMER_MAX * random.uniform(0.6, 1.0)
        self.max_timer = self.timer
        self.state = STATE_AUTHORIZED
        self.evict_timer = 0.0
        self.alive = True

        angle = random.uniform(0, 2 * math.pi)
        r = random.uniform(2.0, HEX_RADIUS * 0.6)
        y = HEX_HEIGHT + random.uniform(-1.0, 1.0)
        self.pos = Vec3(r * math.cos(angle), y, r * math.sin(angle))

        speed = random.uniform(1.2, 2.2)
        va = random.uniform(0, 2 * math.pi)
        self.vel = Vec3(
            speed * math.cos(va),
            random.uniform(-0.15, 0.15),
            speed * math.sin(va),
        )

        # ★ 드론 본체 — unlit=True 자체 발광
        self.entity = Entity(
            model='sphere', scale=0.6,
            color=C_GREEN, position=self.pos,
            unlit=True,
        )

        # 바닥 투영
        self.ground_dot = Entity(
            model='circle', scale=0.6,
            color=C_GREEN, alpha=0.12,
            position=Vec3(self.pos.x, 0.02, self.pos.z),
            rotation_x=90, unlit=True,
        )

        # 수직 드롭 라인
        self.drop_line = Entity(
            model='cube', scale=(0.012, 1, 0.012),
            color=C_GREEN, alpha=0.08,
            position=self.pos, unlit=True,
        )

        # 빌보드 라벨 — background=False, 크게
        self.label = Text(
            text='', scale=5,
            color=C_WHITE,
            position=self.pos + Vec3(0, 1.5, 0),
            billboard=True, origin=(0, 0),
            background=False,
        )

        self.pulse_t = 0.0
        self.base_scale = 0.6
        self._refresh_label()

    def _refresh_label(self):
        if self.timer > 0:
            m = int(self.timer) // 60
            s = int(self.timer) % 60
            t_str = f'{m}:{s:02d}'
        else:
            t_str = '0:00'
        cmap = {
            STATE_AUTHORIZED: C_GREEN,
            STATE_WARNING: C_ORANGE,
            STATE_EXPIRED: C_RED,
            STATE_EVICTING: C_MAGENTA,
        }
        self.label.text = f'UD-{self.idx:02d} | {t_str}'
        self.label.color = cmap.get(self.state, C_WHITE)

    def destroy(self):
        self.alive = False
        destroy(self.entity)
        destroy(self.ground_dot)
        destroy(self.drop_line)
        destroy(self.label)

    def update(self, dt):
        if not self.alive:
            return

        if self.state == STATE_EVICTING:
            self.evict_timer += dt
            outward = Vec3(self.pos.x, 0, self.pos.z).normalized()
            self.pos += outward * 7 * dt
            self.pos.y += 2.5 * dt
            fade = max(0, 1.0 - self.evict_timer / TIMER_EVICT)

            self.entity.color = C_MAGENTA
            self.pulse_t += dt * 12
            blink = 0.4 + 0.6 * abs(math.sin(self.pulse_t))
            self.entity.alpha = fade * blink
            self.ground_dot.alpha = fade * 0.08
            self.drop_line.alpha = fade * 0.04
            self.label.alpha = fade

            p = 1.0 + 0.3 * math.sin(self.pulse_t)
            self.entity.scale = Vec3(self.base_scale * p,
                                     self.base_scale * p,
                                     self.base_scale * p)
            self._sync()
            self._refresh_label()
            if self.evict_timer > TIMER_EVICT:
                self.destroy()
            return

        # Move
        self.pos += self.vel * dt

        dist_xz = math.sqrt(self.pos.x ** 2 + self.pos.z ** 2)
        if dist_xz > HEX_RADIUS * 0.78:
            normal = Vec3(self.pos.x, 0, self.pos.z).normalized()
            dot = self.vel.x * normal.x + self.vel.z * normal.z
            self.vel.x -= 2 * dot * normal.x
            self.vel.z -= 2 * dot * normal.z
            factor = (HEX_RADIUS * 0.76) / max(dist_xz, 0.01)
            self.pos.x *= factor
            self.pos.z *= factor

        if self.pos.y > HEX_HEIGHT + 2.0:
            self.vel.y = -abs(self.vel.y)
        elif self.pos.y < HEX_HEIGHT - 2.0:
            self.vel.y = abs(self.vel.y)

        self.timer -= dt
        if self.timer < 0:
            self.timer = 0

        if self.timer > TIMER_WARN:
            self.state = STATE_AUTHORIZED
            self.entity.color = C_GREEN
            self.entity.alpha = 1.0
            self.ground_dot.color = C_GREEN
            self.drop_line.color = C_GREEN
            self.entity.scale = Vec3(self.base_scale, self.base_scale,
                                     self.base_scale)

        elif self.timer > 0:
            self.state = STATE_WARNING
            t = self.timer / TIMER_WARN
            g = int(80 + 170 * t)
            self.entity.color = color.rgb(255, g, 0)
            self.ground_dot.color = C_ORANGE
            self.drop_line.color = C_ORANGE
            self.pulse_t += dt * 6
            blink = 0.5 + 0.5 * math.sin(self.pulse_t)
            self.entity.alpha = 0.6 + 0.4 * blink
            p = 1.0 + 0.12 * math.sin(self.pulse_t * 1.5)
            self.entity.scale = Vec3(self.base_scale * p,
                                     self.base_scale * p,
                                     self.base_scale * p)

        else:
            if self.state != STATE_EXPIRED:
                self.state = STATE_EXPIRED
                self.evict_timer = 0
            self.entity.color = C_RED
            self.ground_dot.color = C_RED
            self.drop_line.color = C_RED
            self.pulse_t += dt * 10
            blink = 0.3 + 0.7 * abs(math.sin(self.pulse_t))
            self.entity.alpha = blink
            p = 1.0 + 0.25 * math.sin(self.pulse_t * 1.2)
            self.entity.scale = Vec3(self.base_scale * p,
                                     self.base_scale * p,
                                     self.base_scale * p)
            self.evict_timer += dt
            if self.evict_timer > 5.0:
                self.state = STATE_EVICTING
                self.evict_timer = 0

        self._sync()
        self._refresh_label()

    def _sync(self):
        self.entity.position = self.pos
        self.ground_dot.position = Vec3(self.pos.x, 0.02, self.pos.z)
        mid_y = self.pos.y / 2
        self.drop_line.position = Vec3(self.pos.x, mid_y, self.pos.z)
        self.drop_line.scale_y = self.pos.y
        self.label.position = self.pos + Vec3(0, 1.3, 0)


user_drones: list[UserDrone] = []
for _ in range(INITIAL_USER):
    user_drones.append(UserDrone())

# ================================================================
# EVENT LOG
# ================================================================
event_log: list[str] = []
MAX_LOG = 4

def log_event(msg):
    event_log.append(msg)
    if len(event_log) > MAX_LOG:
        event_log.pop(0)

# ================================================================
# HUD — background=False, 시꺼먼 박스 없음
# ================================================================
hud_title = Text(
    text='SWARM-NET AIRSPACE CONTROL',
    position=(-0.86, 0.48), scale=1.5,
    color=C_HUD_TITLE, font='VeraMono.ttf',
    background=False,
)
hud_stats = Text(
    text='', position=(-0.86, 0.44), scale=0.9,
    color=C_WHITE, font='VeraMono.ttf',
    background=False,
)
hud_status = Text(
    text='', position=(0.68, 0.48), scale=0.9,
    color=C_WHITE, font='VeraMono.ttf',
    background=False,
)
hud_log = Text(
    text='', position=(-0.86, -0.43), scale=0.6,
    color=color.rgb(0, 200, 160), font='VeraMono.ttf',
    background=False,
)
Text(
    text='[Space]+  [X]-  [M]esh  [R]eset  [1][2][3]',
    position=(0.15, -0.48), scale=0.45,
    color=color.rgb(40, 55, 70), font='VeraMono.ttf',
    background=False,
)

# ================================================================
# ANIMATION
# ================================================================
swarm_base_y = [p.y for p in swarm_positions]
swarm_time = 0.0

def update():
    global swarm_time
    dt = time.dt
    swarm_time += dt

    for i, drone in enumerate(swarm_drones):
        drone.y = swarm_base_y[i] + math.sin(swarm_time * 1.5 + i) * 0.1

    for idx, line in enumerate(mesh_lines):
        if mesh_visible:
            base_a = 0.4 if idx < NUM_SWARM else 0.08
            line.alpha = base_a + 0.06 * math.sin(swarm_time * 3 + idx * 0.5)
        else:
            line.alpha = 0

    gcs_dish.rotation_y += 20 * dt

    to_remove = []
    for ud in user_drones:
        old = ud.state
        ud.update(dt)
        if not ud.alive:
            to_remove.append(ud)
            log_event(f'UD-{ud.idx:02d} EVICTED')
        elif ud.state != old:
            log_event(f'UD-{ud.idx:02d} -> {ud.state}')
    for ud in to_remove:
        user_drones.remove(ud)

    alive = [ud for ud in user_drones if ud.alive]
    hud_stats.text = f'NODES:{NUM_SWARM}  TRACKED:{len(alive)}'
    na = sum(1 for u in alive if u.state == STATE_AUTHORIZED)
    nw = sum(1 for u in alive if u.state == STATE_WARNING)
    ne = sum(1 for u in alive if u.state == STATE_EXPIRED)
    nv = sum(1 for u in alive if u.state == STATE_EVICTING)
    hud_status.text = f'A:{na} W:{nw}\nE:{ne} V:{nv}'
    hud_log.text = '\n'.join(event_log)

# ================================================================
# INPUT
# ================================================================
def input(key):
    global mesh_visible
    if key == 'space':
        ud = UserDrone()
        user_drones.append(ud)
        log_event(f'UD-{ud.idx:02d} ADDED')
    elif key == 'x':
        alive = [u for u in user_drones if u.alive and u.state != STATE_EVICTING]
        if alive:
            t = alive[-1]
            t.state = STATE_EVICTING
            t.evict_timer = 0
            log_event(f'UD-{t.idx:02d} EVICT')
    elif key == 'm':
        mesh_visible = not mesh_visible
    elif key == 'r':
        for ud in list(user_drones):
            ud.destroy()
        user_drones.clear()
        UserDrone._counter = 0
        for _ in range(INITIAL_USER):
            user_drones.append(UserDrone())
        event_log.clear()
        log_event('RESET')
    elif key == '1':
        camera.position = Vec3(28, 8, 0)
        camera.rotation = Vec3(10, -90, 0)
    elif key == '2':
        camera.position = Vec3(0, 32, -0.1)
        camera.rotation = Vec3(90, 0, 0)
    elif key == '3':
        camera.position = Vec3(0, 22, -30)
        camera.rotation = Vec3(38, 0, 0)

# ================================================================
# CAMERA — 중심부를 바라보며 적절한 줌
# ================================================================
camera.position = Vec3(0, 22, -30)
camera.rotation_x = 38

log_event('SYSTEM ONLINE')
log_event(f'{NUM_SWARM} Sentinels')
log_event(f'{INITIAL_USER} drones')

app.run()
