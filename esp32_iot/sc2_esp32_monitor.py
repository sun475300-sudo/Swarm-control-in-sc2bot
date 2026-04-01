# Phase 640: ESP32 IoT Telemetry Monitor for SC2
# Integrates ESP32 microcontroller with SC2 bot for real-time telemetry display,
# MQTT-based event streaming, LED status indicators, and OLED game stats.

from __future__ import annotations

import json
import time
import struct
import logging
import threading
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import Optional, Callable, Any

logger = logging.getLogger(__name__)

# ============================================================
# Constants
# ============================================================

MQTT_DEFAULT_BROKER = "localhost"
MQTT_DEFAULT_PORT = 1883
TOPIC_GAME_STATE = "sc2/game/state"
TOPIC_ALERTS = "sc2/alerts"
TOPIC_COMMANDS = "sc2/commands"
TOPIC_LED_CONTROL = "sc2/led/control"
MAX_SUPPLY = 200


class LEDColor(Enum):
    OFF = (0, 0, 0)
    RED = (255, 0, 0)
    GREEN = (0, 255, 0)
    YELLOW = (255, 200, 0)
    BLUE = (0, 0, 255)
    WHITE = (255, 255, 255)
    ORANGE = (255, 100, 0)
    PURPLE = (128, 0, 255)


class AlertLevel(Enum):
    NONE = auto()
    INFO = auto()
    WARNING = auto()
    CRITICAL = auto()


class ButtonAction(Enum):
    SCOUT = "scout"
    EXPAND = "expand"
    ATTACK = "attack"
    DEFEND = "defend"
    BUILD_ARMY = "build_army"


# ============================================================
# Data Classes
# ============================================================

@dataclass
class ESP32Config:
    """Configuration for ESP32 connection and hardware pins."""
    broker_host: str = MQTT_DEFAULT_BROKER
    broker_port: int = MQTT_DEFAULT_PORT
    client_id: str = "sc2_esp32_monitor"
    led_pin_red: int = 25
    led_pin_green: int = 26
    led_pin_blue: int = 27
    oled_sda_pin: int = 21
    oled_scl_pin: int = 22
    oled_width: int = 128
    oled_height: int = 64
    button_pins: list[int] = field(default_factory=lambda: [32, 33, 34, 35])
    buzzer_pin: int = 14
    led_brightness: float = 0.8
    enable_buzzer: bool = True
    enable_oled: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ESP32Config:
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in valid})


@dataclass
class TelemetryPacket:
    """Telemetry data packet sent between SC2 bot and ESP32."""
    timestamp: float = 0.0
    game_loop: int = 0
    minerals: int = 0
    vespene: int = 0
    supply_used: int = 0
    supply_cap: int = 0
    army_count: int = 0
    worker_count: int = 0
    enemy_detected: bool = False
    under_attack: bool = False
    base_count: int = 1
    tech_level: int = 1
    current_strategy: str = "macro"
    apm: float = 0.0
    win_probability: float = 0.5

    def serialize(self) -> bytes:
        payload = json.dumps(asdict(self)).encode("utf-8")
        header = struct.pack("!HH", 0xABCD, len(payload))
        return header + payload

    @classmethod
    def deserialize(cls, data: bytes) -> TelemetryPacket:
        if len(data) < 4:
            return cls()
        _magic, length = struct.unpack("!HH", data[:4])
        payload = json.loads(data[4:4 + length].decode("utf-8"))
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in payload.items() if k in valid})

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, raw: str) -> TelemetryPacket:
        data = json.loads(raw)
        valid = {f.name for f in cls.__dataclass_fields__.values()}
        return cls(**{k: v for k, v in data.items() if k in valid})

    def supply_ratio(self) -> float:
        return self.supply_used / self.supply_cap if self.supply_cap else 0.0


# ============================================================
# MQTT Bridge
# ============================================================

class MQTTBridge:
    """MQTT bridge for communication between SC2 bot and ESP32 hardware."""

    def __init__(self, config: ESP32Config) -> None:
        self.config = config
        self._connected = False
        self._subscriptions: dict[str, list[Callable[[str, bytes], None]]] = {}
        self._publish_count = 0
        self._receive_count = 0
        self._lock = threading.Lock()
        logger.info("MQTTBridge init: %s:%d", config.broker_host, config.broker_port)

    def connect(self) -> bool:
        self._connected = True
        logger.info("MQTT connected (mock)")
        return True

    def disconnect(self) -> None:
        self._connected = False
        logger.info("MQTT disconnected")

    def publish(self, topic: str, payload: Any) -> bool:
        if not self._connected:
            return False
        if isinstance(payload, (dict, list)):
            data = json.dumps(payload).encode("utf-8")
        elif isinstance(payload, str):
            data = payload.encode("utf-8")
        elif isinstance(payload, bytes):
            data = payload
        else:
            data = str(payload).encode("utf-8")
        with self._lock:
            self._publish_count += 1
        self._dispatch(topic, data)
        return True

    def subscribe(self, topic: str, callback: Callable[[str, bytes], None]) -> None:
        with self._lock:
            self._subscriptions.setdefault(topic, []).append(callback)
        logger.info("Subscribed: %s", topic)

    def _dispatch(self, topic: str, data: bytes) -> None:
        with self._lock:
            callbacks = []
            for pattern, cbs in self._subscriptions.items():
                if self._match(pattern, topic):
                    callbacks.extend(cbs)
        for cb in callbacks:
            try:
                cb(topic, data)
                with self._lock:
                    self._receive_count += 1
            except Exception as exc:
                logger.error("Callback error on %s: %s", topic, exc)

    @staticmethod
    def _match(pattern: str, topic: str) -> bool:
        if pattern == topic:
            return True
        if pattern.endswith("#"):
            return topic.startswith(pattern[:-1])
        pp, pt = pattern.split("/"), topic.split("/")
        if len(pp) != len(pt):
            return False
        return all(a == "+" or a == b for a, b in zip(pp, pt))

    def get_stats(self) -> dict[str, Any]:
        with self._lock:
            return {"connected": self._connected, "published": self._publish_count,
                    "received": self._receive_count, "topics": list(self._subscriptions)}


# ============================================================
# LED Controller
# ============================================================

class LEDController:
    """RGB LED controller for SC2 game status visualization."""

    def __init__(self, config: ESP32Config) -> None:
        self.config = config
        self._current = LEDColor.OFF
        self._flash_active = False
        self._flash_stop = threading.Event()
        self._brightness = config.led_brightness
        self._history: list[dict[str, Any]] = []

    def set_color(self, color: LEDColor) -> None:
        self._stop_flash()
        self._current = color
        self._write(self._scale(*color.value))
        self._history.append({"action": "set", "color": color.name, "t": time.time()})

    def flash(self, color: LEDColor, interval: float = 0.3, count: int = 0) -> None:
        self._stop_flash()
        self._flash_stop.clear()
        self._flash_active = True

        def loop() -> None:
            i = 0
            while not self._flash_stop.is_set():
                if count > 0 and i >= count:
                    break
                self._write(self._scale(*color.value))
                self._flash_stop.wait(interval)
                self._write((0, 0, 0))
                self._flash_stop.wait(interval)
                i += 1
            self._flash_active = False

        threading.Thread(target=loop, daemon=True).start()
        self._history.append({"action": "flash", "color": color.name, "t": time.time()})

    def _stop_flash(self) -> None:
        if self._flash_active:
            self._flash_stop.set()
            self._flash_active = False

    def _scale(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        f = self._brightness
        return int(r * f), int(g * f), int(b * f)

    def _write(self, rgb: tuple[int, int, int]) -> None:
        logger.debug("LED <- RGB%s", rgb)

    def update_from_supply(self, used: int, cap: int) -> None:
        if cap == 0:
            self.set_color(LEDColor.BLUE); return
        ratio = used / cap
        if ratio < 0.5:
            self.set_color(LEDColor.GREEN)
        elif ratio < 0.8:
            self.set_color(LEDColor.YELLOW)
        elif ratio < 0.95:
            self.set_color(LEDColor.ORANGE)
        else:
            self.set_color(LEDColor.RED)

    def alert_under_attack(self) -> None:
        self.flash(LEDColor.RED, interval=0.15)

    def alert_enemy_spotted(self) -> None:
        self.flash(LEDColor.YELLOW, interval=0.3, count=5)

    def victory_animation(self) -> None:
        self.flash(LEDColor.GREEN, interval=0.2, count=10)

    def off(self) -> None:
        self._stop_flash()
        self.set_color(LEDColor.OFF)

    def get_history(self) -> list[dict[str, Any]]:
        return list(self._history)


# ============================================================
# OLED Display Simulator
# ============================================================

class OLEDDisplay:
    """Simulated OLED display for SC2 game information."""

    def __init__(self, config: ESP32Config) -> None:
        self.width = config.oled_width
        self.height = config.oled_height
        self._lines: list[str] = []
        self._max_lines = self.height // 10
        self._frames = 0

    def clear(self) -> None:
        self._lines = []

    def write_line(self, text: str, line: int = -1) -> None:
        text = text[:self.width // 6]
        if 0 <= line < self._max_lines:
            while len(self._lines) <= line:
                self._lines.append("")
            self._lines[line] = text
        else:
            if len(self._lines) < self._max_lines:
                self._lines.append(text)
            else:
                self._lines.pop(0)
                self._lines.append(text)

    def render_game_state(self, pkt: TelemetryPacket) -> None:
        self.clear()
        self.write_line(f"Min:{pkt.minerals:>5} Gas:{pkt.vespene:>4}", 0)
        self.write_line(f"Supply: {pkt.supply_used}/{pkt.supply_cap}", 1)
        self.write_line(f"Army:{pkt.army_count:>3} Wrk:{pkt.worker_count:>3}", 2)
        self.write_line(f"Bases:{pkt.base_count} Tech:{pkt.tech_level}", 3)
        self.write_line(f"Strat: {pkt.current_strategy[:14]}", 4)
        if pkt.under_attack:
            self.write_line("!! UNDER ATTACK !!", 5)
        elif pkt.enemy_detected:
            self.write_line("* Enemy spotted *", 5)
        else:
            self.write_line(f"Win%:{int(pkt.win_probability*100)} APM:{pkt.apm:.0f}", 5)
        self._frames += 1

    def get_display_text(self) -> str:
        top = "+" + "-" * 21 + "+"
        rows = [top]
        for i in range(self._max_lines):
            t = self._lines[i] if i < len(self._lines) else ""
            rows.append(f"|{t:<21}|")
        rows.append(top)
        return "\n".join(rows)


# ============================================================
# Button / Sensor Simulator
# ============================================================

class ButtonController:
    """Simulates button inputs on ESP32 GPIO for game commands."""

    def __init__(self, config: ESP32Config) -> None:
        actions = list(ButtonAction)
        self._pin_map: dict[int, ButtonAction] = {
            pin: actions[i] for i, pin in enumerate(config.button_pins) if i < len(actions)
        }
        self._log: list[dict[str, Any]] = []
        self._callbacks: dict[ButtonAction, Callable[[], None]] = {}

    def register_callback(self, action: ButtonAction, cb: Callable[[], None]) -> None:
        self._callbacks[action] = cb

    def simulate_press(self, pin: int) -> Optional[ButtonAction]:
        action = self._pin_map.get(pin)
        if action is None:
            return None
        self._log.append({"pin": pin, "action": action.value, "t": time.time()})
        cb = self._callbacks.get(action)
        if cb:
            cb()
        return action

    def simulate_action(self, action: ButtonAction) -> dict[str, str]:
        cmd = {"action": action.value, "source": "esp32_button", "ts": str(time.time())}
        self._log.append({"action": action.value, "t": time.time()})
        return cmd

    def get_pin_map(self) -> dict[int, str]:
        return {p: a.value for p, a in self._pin_map.items()}

    def get_log(self) -> list[dict[str, Any]]:
        return list(self._log)


# ============================================================
# Buzzer Controller
# ============================================================

class BuzzerController:
    """Piezo buzzer for audio alerts."""

    def __init__(self, config: ESP32Config) -> None:
        self.pin = config.buzzer_pin
        self.enabled = config.enable_buzzer
        self._tones: list[dict[str, Any]] = []

    def beep(self, freq: int = 1000, ms: int = 200) -> None:
        if not self.enabled:
            return
        self._tones.append({"freq": freq, "ms": ms, "t": time.time()})

    def alert_tone(self) -> None:
        for _ in range(3):
            self.beep(2000, 100)

    def victory_tone(self) -> None:
        for f in [523, 659, 784, 1047]:
            self.beep(f, 250)


# ============================================================
# ESP32 Monitor (Main Coordinator)
# ============================================================

class ESP32Monitor:
    """Main coordinator: ties MQTT, LEDs, OLED, buttons, and buzzer together."""

    def __init__(self, config: Optional[ESP32Config] = None) -> None:
        self.config = config or ESP32Config()
        self.mqtt = MQTTBridge(self.config)
        self.leds = LEDController(self.config)
        self.oled = OLEDDisplay(self.config)
        self.buttons = ButtonController(self.config)
        self.buzzer = BuzzerController(self.config)
        self._latest: Optional[TelemetryPacket] = None
        self._running = False
        self._events: list[dict[str, Any]] = []

    def start(self) -> bool:
        if not self.mqtt.connect():
            return False
        self.mqtt.subscribe(TOPIC_GAME_STATE, self._on_game_state)
        self.mqtt.subscribe(TOPIC_ALERTS, self._on_alert)
        self.mqtt.subscribe(TOPIC_LED_CONTROL, self._on_led_control)
        for action in ButtonAction:
            self.buttons.register_callback(action, lambda a=action: self._send_cmd(a))
        self._running = True
        self.leds.set_color(LEDColor.BLUE)
        self.oled.write_line("SC2 Monitor Ready", 0)
        return True

    def stop(self) -> None:
        self._running = False
        self.leds.off()
        self.oled.clear()
        self.mqtt.disconnect()

    def _send_cmd(self, action: ButtonAction) -> None:
        self.mqtt.publish(TOPIC_COMMANDS, self.buttons.simulate_action(action))

    def _on_game_state(self, topic: str, data: bytes) -> None:
        try:
            pkt = TelemetryPacket.from_json(data.decode("utf-8"))
            self._latest = pkt
            self.oled.render_game_state(pkt)
            self.leds.update_from_supply(pkt.supply_used, pkt.supply_cap)
            if pkt.under_attack:
                self.leds.alert_under_attack()
                self.buzzer.alert_tone()
            self._events.append({"type": "state", "loop": pkt.game_loop})
        except Exception as exc:
            logger.error("Game state error: %s", exc)

    def _on_alert(self, topic: str, data: bytes) -> None:
        try:
            alert = json.loads(data.decode("utf-8"))
            level = AlertLevel[alert.get("level", "INFO").upper()]
            if level == AlertLevel.CRITICAL:
                self.leds.alert_under_attack()
                self.buzzer.alert_tone()
            elif level == AlertLevel.WARNING:
                self.leds.alert_enemy_spotted()
        except Exception as exc:
            logger.error("Alert error: %s", exc)

    def _on_led_control(self, topic: str, data: bytes) -> None:
        try:
            cmd = json.loads(data.decode("utf-8"))
            color = LEDColor[cmd.get("color", "OFF").upper()]
            if cmd.get("flash"):
                self.leds.flash(color, interval=cmd.get("interval", 0.3))
            else:
                self.leds.set_color(color)
        except Exception as exc:
            logger.error("LED control error: %s", exc)

    def publish_telemetry(self, pkt: TelemetryPacket) -> bool:
        return self.mqtt.publish(TOPIC_GAME_STATE, pkt.to_json())

    def publish_alert(self, level: AlertLevel, message: str) -> bool:
        return self.mqtt.publish(TOPIC_ALERTS, {"level": level.name, "message": message})

    def simulate_game_tick(self, game_loop: int, minerals: int, vespene: int,
                           supply_used: int, supply_cap: int, army_count: int = 0,
                           worker_count: int = 16, under_attack: bool = False,
                           enemy_detected: bool = False) -> TelemetryPacket:
        pkt = TelemetryPacket(
            timestamp=time.time(), game_loop=game_loop,
            minerals=minerals, vespene=vespene,
            supply_used=supply_used, supply_cap=supply_cap,
            army_count=army_count, worker_count=worker_count,
            under_attack=under_attack, enemy_detected=enemy_detected,
            base_count=max(1, supply_cap // 50),
            tech_level=min(3, 1 + game_loop // 5000),
            current_strategy="rush" if game_loop < 3000 else "macro",
            apm=120.0 + (game_loop % 80),
            win_probability=min(0.95, 0.4 + army_count * 0.01),
        )
        self.publish_telemetry(pkt)
        return pkt

    def get_status(self) -> dict[str, Any]:
        return {"running": self._running, "mqtt": self.mqtt.get_stats(),
                "led_events": len(self.leds.get_history()),
                "oled_frames": self.oled._frames,
                "button_presses": len(self.buttons.get_log()),
                "events": len(self._events)}


# ============================================================
# Demo
# ============================================================

def demo() -> None:
    """Demonstrate ESP32 IoT Monitor with mock MQTT and simulated game ticks."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    print("=" * 60)
    print(" Phase 640: ESP32 IoT Telemetry Monitor - Demo")
    print("=" * 60)

    config = ESP32Config(broker_host="localhost", broker_port=1883, led_brightness=1.0)
    monitor = ESP32Monitor(config)
    assert monitor.start(), "Monitor failed to start"

    print(f"\n[1] Config: {config.broker_host}:{config.broker_port}")
    print(f"  OLED: {config.oled_width}x{config.oled_height}  Buttons: {config.button_pins}")

    print("\n[2] Simulating early game")
    for loop in range(0, 4000, 800):
        pkt = monitor.simulate_game_tick(
            game_loop=loop, minerals=300 + loop // 10, vespene=50 + loop // 20,
            supply_used=12 + loop // 200, supply_cap=14 + (loop // 800) * 8,
            army_count=loop // 500, worker_count=min(66, 12 + loop // 300),
        )
        print(f"  Loop {loop}: supply={pkt.supply_used}/{pkt.supply_cap}")

    print("\n[3] OLED Display:")
    print(monitor.oled.get_display_text())

    print("\n[4] Attack alert")
    monitor.publish_alert(AlertLevel.CRITICAL, "Zerglings at natural!")
    atk = monitor.simulate_game_tick(
        game_loop=5000, minerals=800, vespene=400, supply_used=120,
        supply_cap=150, army_count=45, worker_count=55, under_attack=True,
    )
    print(f"  Under attack: {atk.supply_used}/{atk.supply_cap}")
    print(monitor.oled.get_display_text())

    print("\n[5] Button presses")
    for pin in config.button_pins[:3]:
        act = monitor.buttons.simulate_press(pin)
        if act:
            print(f"  Pin {pin} -> {act.value}")

    print("\n[6] Serialization test")
    test = TelemetryPacket(minerals=1200, vespene=800, supply_used=180, supply_cap=200)
    restored = TelemetryPacket.deserialize(test.serialize())
    print(f"  Original: min={test.minerals}  Restored: min={restored.minerals}")
    assert test.minerals == restored.minerals

    print("\n[7] Status:", monitor.get_status())
    monitor.stop()
    print("\n[OK] Demo complete.")


if __name__ == "__main__":
    demo()

# Phase 640: ESP32 registered
