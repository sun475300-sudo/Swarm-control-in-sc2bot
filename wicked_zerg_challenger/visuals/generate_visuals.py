"""
Swarm-Net Presentation Visual Asset Generator
==============================================
텍스트 없는 순수 도형/라인 기반 시각자료 생성
PPTX 텍스트와 겹침 방지 — 장식용 배경 그래픽 전용
"""

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon
from pathlib import Path

# ===== Color constants (matching PPTX theme) =====
BG_DARK = '#0B101F'
BG_CARD = '#121A2E'
CYAN = '#00FFCC'
CYAN_DIM = '#00B894'
ORANGE = '#FF9800'
RED = '#FF4545'
GREEN = '#00E676'
WHITE = '#FFFFFF'
LIGHT = '#E8E8E8'
DIM = '#A0A8B8'
PURPLE = '#B388FF'
GOLD = '#FFD700'

OUT_DIR = Path(__file__).parent / "images"
OUT_DIR.mkdir(exist_ok=True)


def save_fig(fig, name, dpi=200):
    path = OUT_DIR / name
    fig.savefig(str(path), dpi=dpi, bbox_inches='tight',
                facecolor=fig.get_facecolor(), edgecolor='none',
                transparent=False)
    plt.close(fig)
    print(f"  [OK] {name}")


# ===================================================================
# Slide 1: Hexagonal Swarm Network (no text)
# ===================================================================
def gen_slide1():
    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)
    ax.set_xlim(-3, 3)
    ax.set_ylim(-3, 3)
    ax.set_aspect('equal')
    ax.axis('off')

    angles = np.linspace(0, 2 * np.pi, 7)[:-1]
    r = 1.8
    cx, cy = np.cos(angles) * r, np.sin(angles) * r
    positions = [(0, 0)] + list(zip(cx, cy))

    # Mesh connections
    for i, (x1, y1) in enumerate(positions):
        for j, (x2, y2) in enumerate(positions):
            if i < j:
                dist = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
                if dist < 2.5:
                    alpha = max(0.15, 1.0 - dist / 3.0)
                    ax.plot([x1, x2], [y1, y2], color=CYAN, alpha=alpha * 0.5,
                            linewidth=1.2)

    # Radar dome circles
    for rad in [1.0, 1.8, 2.5]:
        circle = plt.Circle((0, 0), rad, fill=False, color=CYAN,
                             alpha=0.15, linewidth=1, linestyle='--')
        ax.add_patch(circle)

    # Drones
    for i, (x, y) in enumerate(positions):
        size = 0.22 if i == 0 else 0.18
        color = CYAN if i == 0 else CYAN_DIM
        c = plt.Circle((x, y), size, color=color, alpha=0.9 if i == 0 else 0.7)
        ax.add_patch(c)
        ax.plot(x, y, 'o', color=WHITE, markersize=4 if i == 0 else 3, zorder=5)

        if i > 0:
            for wave_r in [0.35, 0.5]:
                wave = plt.Circle((x, y), wave_r, fill=False, color=CYAN,
                                  alpha=0.2, linewidth=0.8)
                ax.add_patch(wave)

    save_fig(fig, 'slide1_swarm_hex.png')


# ===================================================================
# Slide 2: Radar Coverage Gap (no text)
# ===================================================================
def gen_slide2():
    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    ax.axis('off')

    # Terrain
    terrain_x = np.linspace(0, 10, 200)
    terrain_y = 0.8 + 0.3 * np.sin(terrain_x * 1.5) + 0.2 * np.sin(terrain_x * 3)
    ax.fill_between(terrain_x, 0, terrain_y, color='#1A2540', alpha=0.8)
    ax.plot(terrain_x, terrain_y, color='#2A3A5A', linewidth=1)

    # Mountains
    m1 = Polygon([(2.5, 0.8), (3.5, 3.0), (4.5, 0.8)],
                  closed=True, facecolor='#1E2A45', edgecolor='#2A3A5A')
    m2 = Polygon([(6.0, 0.8), (7.0, 2.5), (8.0, 0.8)],
                  closed=True, facecolor='#1E2A45', edgecolor='#2A3A5A')
    ax.add_patch(m1)
    ax.add_patch(m2)

    # Radar tower
    tower_x, tower_y = 1.0, 1.2
    ax.plot([tower_x, tower_x], [tower_y, tower_y + 0.8], color=RED, linewidth=3)
    ax.plot(tower_x, tower_y + 0.8, '^', color=RED, markersize=12)

    # Coverage arc
    theta = np.linspace(-0.1, np.pi + 0.1, 100)
    radar_r = 5.0
    rx = tower_x + radar_r * np.cos(theta)
    ry = tower_y + 0.8 + radar_r * np.sin(theta)
    for i in range(len(theta) - 1):
        mid_angle = (theta[i] + theta[i + 1]) / 2
        mid_x = tower_x + 2 * np.cos(mid_angle)
        is_blocked = (2.5 < mid_x < 4.5) or (6.0 < mid_x < 8.0)
        color = RED if is_blocked else CYAN
        ax.plot([rx[i], rx[i + 1]], [ry[i], ry[i + 1]],
                color=color, alpha=0.4, linewidth=1.5)

    # Blind spot shading
    ax.fill([3.0, 4.0, 5.5, 4.5, 3.5], [3.0, 3.5, 5.0, 5.5, 4.0],
            color=RED, alpha=0.12)
    ax.fill([6.5, 7.5, 9.0, 8.5, 7.0], [2.5, 3.0, 4.5, 5.0, 3.5],
            color=RED, alpha=0.12)

    # Undetected drones
    for dx, dy in [(4.0, 4.5), (7.5, 4.0)]:
        ax.plot(dx, dy, 's', color=ORANGE, markersize=8, alpha=0.8)

    # Legend lines (no text)
    ax.plot([1.0, 2.5], [6.3, 6.3], color=CYAN, alpha=0.4, linewidth=2)
    ax.plot([5.5, 7.0], [6.3, 6.3], color=RED, alpha=0.4, linewidth=2)

    save_fig(fig, 'slide2_radar_gap.png')


# ===================================================================
# Slide 3: Mobile ATC Architecture (no text)
# ===================================================================
def gen_slide3():
    fig, ax = plt.subplots(figsize=(6, 5))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.set_aspect('equal')
    ax.axis('off')

    center = (5, 4)
    hex_r = 1.5
    angles = np.linspace(0, 2 * np.pi, 7)[:-1]
    drones = [(center[0] + hex_r * np.cos(a), center[1] + hex_r * np.sin(a))
              for a in angles]
    drones.insert(0, center)

    # Mesh connections
    for i, (x1, y1) in enumerate(drones):
        for j, (x2, y2) in enumerate(drones):
            if i < j:
                d = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
                if d < 2.2:
                    ax.plot([x1, x2], [y1, y2], color=CYAN, alpha=0.3, linewidth=1)

    # Dome
    dome = plt.Circle(center, 2.5, fill=False, color=CYAN, alpha=0.25,
                       linewidth=2, linestyle='--')
    ax.add_patch(dome)
    dome_fill = plt.Circle(center, 2.5, fill=True, color=CYAN, alpha=0.04)
    ax.add_patch(dome_fill)

    # Swarm drones
    for i, (x, y) in enumerate(drones):
        size = 0.2 if i == 0 else 0.15
        color = CYAN if i == 0 else GREEN
        c = plt.Circle((x, y), size, color=color, alpha=0.85, zorder=5)
        ax.add_patch(c)
        tri_s = size * 1.5
        tri = Polygon([(x, y + tri_s), (x - tri_s * 0.7, y - tri_s * 0.5),
                        (x + tri_s * 0.7, y - tri_s * 0.5)],
                       closed=True, fill=False, edgecolor=WHITE, linewidth=0.8,
                       alpha=0.6, zorder=6)
        ax.add_patch(tri)

    # Intruder
    intruder = (7.5, 3.5)
    ax.plot(*intruder, 's', color=RED, markersize=10, zorder=5)
    # Arrow to intruder (no text)
    ax.annotate("", xy=intruder, xytext=(intruder[0] + 0.8, intruder[1] + 0.8),
                arrowprops=dict(arrowstyle='->', color=RED, lw=1.2))

    # Trilateration lines
    for dx, dy in drones[1:4]:
        ax.plot([dx, intruder[0]], [dy, intruder[1]], color=ORANGE,
                alpha=0.3, linewidth=1, linestyle=':')

    # Ground station box
    gs_x, gs_y = 2.0, 1.0
    gs_rect = FancyBboxPatch((gs_x - 0.3, gs_y - 0.2), 0.6, 0.4,
                              boxstyle="round,pad=0.08",
                              facecolor=BG_CARD, edgecolor=CYAN_DIM, linewidth=1.5)
    ax.add_patch(gs_rect)

    # Link GCS to center
    ax.annotate("", xy=center, xytext=(gs_x, gs_y + 0.2),
                arrowprops=dict(arrowstyle='->', color=CYAN_DIM, lw=1.5,
                                linestyle='--'))

    save_fig(fig, 'slide3_mobile_atc.png')


# ===================================================================
# Slide 5: 3D Tracking (no axis labels, no text)
# ===================================================================
def gen_slide5():
    fig = plt.figure(figsize=(7, 5))
    ax = fig.add_subplot(111, projection='3d')
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)

    ax.xaxis.pane.fill = False
    ax.yaxis.pane.fill = False
    ax.zaxis.pane.fill = False
    ax.xaxis.pane.set_edgecolor('#1E2A45')
    ax.yaxis.pane.set_edgecolor('#1E2A45')
    ax.zaxis.pane.set_edgecolor('#1E2A45')

    # Hide all axis text
    ax.set_xticklabels([])
    ax.set_yticklabels([])
    ax.set_zticklabels([])
    ax.set_xlabel('')
    ax.set_ylabel('')
    ax.set_zlabel('')
    ax.tick_params(length=0)

    ax.xaxis._axinfo['grid']['color'] = '#1E2A45'
    ax.yaxis._axinfo['grid']['color'] = '#1E2A45'
    ax.zaxis._axinfo['grid']['color'] = '#1E2A45'

    np.random.seed(42)
    n_swarm = 6
    angles = np.linspace(0, 2 * np.pi, n_swarm + 1)[:-1]
    r = 30
    sx = r * np.cos(angles) + 50
    sy = r * np.sin(angles) + 50
    sz = np.array([80, 85, 75, 82, 78, 88])

    ax.scatter(sx, sy, sz, c=CYAN, s=60, marker='^', alpha=0.9, zorder=5,
               edgecolors=WHITE, linewidth=0.5)

    for i in range(n_swarm):
        for j in range(i + 1, n_swarm):
            ax.plot([sx[i], sx[j]], [sy[i], sy[j]], [sz[i], sz[j]],
                    color=CYAN, alpha=0.2, linewidth=0.8)

    ax.scatter([50], [50], [90], c=CYAN, s=100, marker='o', alpha=0.9,
               edgecolors=WHITE, linewidth=1, zorder=6)

    # Intruder path
    t = np.linspace(0, 2 * np.pi, 50)
    ix = 50 + 15 * np.cos(t) + np.random.randn(50) * 1.5
    iy = 50 + 10 * np.sin(t) + np.random.randn(50) * 1.5
    iz = 60 + 5 * np.sin(2 * t)

    ax.plot(ix, iy, iz, color=ORANGE, alpha=0.5, linewidth=1.5)
    ax.scatter([ix[-1]], [iy[-1]], [iz[-1]], c=RED, s=80, marker='s',
               alpha=0.9, zorder=5, edgecolors=WHITE, linewidth=0.5)

    ax.plot(ix, iy, np.zeros_like(iz), color=ORANGE, alpha=0.15, linewidth=0.8)
    ax.plot([ix[-1], ix[-1]], [iy[-1], iy[-1]], [0, iz[-1]],
            color=ORANGE, alpha=0.2, linewidth=0.8, linestyle=':')

    # Dome wireframe
    u = np.linspace(0, 2 * np.pi, 30)
    v = np.linspace(0, np.pi / 2, 15)
    dome_r = 45
    x_dome = dome_r * np.outer(np.cos(u), np.sin(v)) + 50
    y_dome = dome_r * np.outer(np.sin(u), np.sin(v)) + 50
    z_dome = dome_r * np.outer(np.ones_like(u), np.cos(v)) + 10
    ax.plot_wireframe(x_dome, y_dome, z_dome, color=CYAN, alpha=0.06, linewidth=0.3)

    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.set_zlim(0, 100)
    ax.view_init(elev=25, azim=135)

    save_fig(fig, 'slide5_3d_tracking.png', dpi=180)


# ===================================================================
# Slide 6: Timer Gauges (no text)
# ===================================================================
def gen_slide6():
    fig, axes = plt.subplots(1, 4, figsize=(8, 3))
    fig.patch.set_facecolor(BG_DARK)

    statuses = [
        (GREEN, 0.85),
        (ORANGE, 0.25),
        (RED, 0.0),
        ('#FF0044', -0.1),
    ]

    for ax_i, (color, pct) in zip(axes, statuses):
        ax_i.set_facecolor(BG_DARK)
        ax_i.set_xlim(-1.5, 1.5)
        ax_i.set_ylim(-1.5, 1.5)
        ax_i.set_aspect('equal')
        ax_i.axis('off')

        theta_bg = np.linspace(0, 2 * np.pi, 100)
        ax_i.plot(np.cos(theta_bg), np.sin(theta_bg), color='#1E2A45',
                  linewidth=8, alpha=0.5)

        if pct > 0:
            theta_fg = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi * pct, 100)
            ax_i.plot(np.cos(theta_fg), np.sin(theta_fg), color=color,
                      linewidth=8, alpha=0.8)
        elif pct <= 0:
            ax_i.plot(np.cos(theta_bg), np.sin(theta_bg), color=color,
                      linewidth=8, alpha=0.6)

        # Center dot
        ax_i.plot(0, 0, 'o', color=color, markersize=6, alpha=0.6)

    plt.subplots_adjust(wspace=0.15)
    save_fig(fig, 'slide6_timer_dash.png')


# ===================================================================
# Slide 7: Coverage Comparison (no text)
# ===================================================================
def gen_slide7():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8, 4))
    fig.patch.set_facecolor(BG_DARK)

    for ax in (ax1, ax2):
        ax.set_facecolor(BG_DARK)
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 8)
        ax.set_aspect('equal')
        ax.axis('off')

    # Left: Fixed Radar
    ax1.plot([2.5, 2.5], [1.0, 2.0], color=RED, linewidth=3)
    ax1.plot(2.5, 2.0, '^', color=RED, markersize=14)
    coverage = plt.Circle((2.5, 2.0), 3.0, fill=True, color=RED, alpha=0.08)
    ax1.add_patch(coverage)
    cov_line = plt.Circle((2.5, 2.0), 3.0, fill=False, color=RED,
                            alpha=0.3, linewidth=1.5, linestyle='--')
    ax1.add_patch(cov_line)
    for bx, by in [(7, 5), (8, 3), (6, 6), (1, 6)]:
        ax1.plot(bx, by, 'x', color=RED, markersize=12, markeredgewidth=2, alpha=0.5)

    # Right: Swarm-Net
    drone_positions = [(3, 4), (5, 5.5), (7, 4), (5, 2.5), (2, 6), (8, 6)]
    for dx, dy in drone_positions:
        ax2.plot(dx, dy, '^', color=CYAN, markersize=8, alpha=0.9)
        cov = plt.Circle((dx, dy), 1.5, fill=True, color=GREEN, alpha=0.06)
        ax2.add_patch(cov)
        cov_line = plt.Circle((dx, dy), 1.5, fill=False, color=GREEN,
                               alpha=0.2, linewidth=0.8, linestyle='--')
        ax2.add_patch(cov_line)

    for i, (x1, y1) in enumerate(drone_positions):
        for j, (x2, y2) in enumerate(drone_positions):
            if i < j:
                d = np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)
                if d < 4.0:
                    ax2.plot([x1, x2], [y1, y2], color=CYAN, alpha=0.2, linewidth=0.8)

    # VS divider line
    fig.patches.append(plt.Rectangle((0.495, 0.1), 0.01, 0.8,
                                      transform=fig.transFigure,
                                      facecolor=GOLD, alpha=0.3))

    save_fig(fig, 'slide7_comparison.png')


# ===================================================================
# Slide 8: Roadmap Progress (no text)
# ===================================================================
def gen_slide8():
    fig, ax = plt.subplots(figsize=(8, 3))
    fig.patch.set_facecolor(BG_DARK)
    ax.set_facecolor(BG_DARK)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 3)
    ax.axis('off')

    stages = [
        (GREEN, 1.0),
        (GREEN, 1.0),
        (ORANGE, 0.3),
        (PURPLE, 0.0),
    ]

    for i, (color, progress) in enumerate(stages):
        cx = 1.3 + i * 2.2
        cy = 1.5

        # Connection line
        if i < 3:
            next_x = cx + 2.2
            ax.plot([cx + 0.5, next_x - 0.5], [cy, cy], color='#1E2A45',
                    linewidth=3, solid_capstyle='round')
            if stages[i + 1][1] > 0:
                ax.plot([cx + 0.5, next_x - 0.5], [cy, cy], color=color,
                        linewidth=3, solid_capstyle='round', alpha=0.5)

        node_bg = plt.Circle((cx, cy), 0.45, fill=True, color=BG_CARD, zorder=3)
        ax.add_patch(node_bg)

        theta_bg = np.linspace(0, 2 * np.pi, 100)
        ax.plot(cx + 0.45 * np.cos(theta_bg), cy + 0.45 * np.sin(theta_bg),
                color='#1E2A45', linewidth=4, zorder=4)

        if progress > 0:
            theta_fg = np.linspace(np.pi / 2, np.pi / 2 - 2 * np.pi * progress, 100)
            ax.plot(cx + 0.45 * np.cos(theta_fg), cy + 0.45 * np.sin(theta_fg),
                    color=color, linewidth=4, zorder=5)

        # Center indicator
        if progress >= 1.0:
            ax.plot(cx, cy, 'o', color=color, markersize=10, zorder=6)
        else:
            ax.plot(cx, cy, 'o', color=color, markersize=6, alpha=0.5, zorder=6)

    save_fig(fig, 'slide8_roadmap.png')


# ===================================================================
def main():
    print(f"Generating visuals in: {OUT_DIR}")
    gen_slide1()
    gen_slide2()
    gen_slide3()
    gen_slide5()
    gen_slide6()
    gen_slide7()
    gen_slide8()
    print(f"\nAll visual assets generated in {OUT_DIR}")


if __name__ == "__main__":
    main()
