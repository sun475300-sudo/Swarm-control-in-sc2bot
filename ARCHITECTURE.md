# System Architecture

## ¾ÆÅ°ÅØÃ³ °³¿ä

Swarm Control in SC2BotÀº 3-Tier ±¸Á¶¸¦ °¡Áø Áö´ÉÇü ÅëÇÕ °üÁ¦ ½Ã½ºÅÛÀÔ´Ï´Ù.

```
¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
¦¢                  Edge Device (Simulation)               ¦¢
¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤   ¦¢
¦¢  ¦¢  StarCraft II Engine                           ¦¢   ¦¢
¦¢  ¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  Wicked Zerg AI Bot                       ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤ ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤ ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤   ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  ¦¢ Economy ¦¢ ¦¢Combat   ¦¢ ¦¢Production¦¢   ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  ¦¢ Manager ¦¢ ¦¢Manager  ¦¢ ¦¢ Manager ¦¢   ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥ ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥ ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥   ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥ ¦¢   ¦¢
¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥   ¦¢
¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥
                          ¦¢
                          ¦¢ Telemetry Data
                          ¡å
¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
¦¢              Cloud Intelligence (Vertex AI)             ¦¢
¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤   ¦¢
¦¢  ¦¢  Gemini 1.5 Pro API                            ¦¢   ¦¢
¦¢  ¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  Self-Healing System                      ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  - Error Detection                        ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  - Code Analysis                          ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  - Auto-Patching                          ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥ ¦¢   ¦¢
¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥   ¦¢
¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥
                          ¦¢
                          ¦¢ Monitoring Data
                          ¡å
¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
¦¢          Remote Monitoring (Mobile GCS)                 ¦¢
¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤   ¦¢
¦¢  ¦¢  Flask Dashboard Server                        ¦¢   ¦¢
¦¢  ¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  FastAPI Backend                          ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  - Real-time Telemetry                    ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  - Win Rate Statistics                    ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¢  - Resource Monitoring                    ¦¢ ¦¢   ¦¢
¦¢  ¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥ ¦¢   ¦¢
¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥   ¦¢
¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤   ¦¢
¦¢  ¦¢  Android Mobile App                            ¦¢   ¦¢
¦¢  ¦¢  - Live Dashboard                              ¦¢   ¦¢
¦¢  ¦¢  - Unit Status                                ¦¢   ¦¢
¦¢  ¦¢  - Performance Metrics                        ¦¢   ¦¢
¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥   ¦¢
¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥
```

---

## ÇÙ½É ÄÄÆ÷³ÍÆ®

### 1. Bot Core (`wicked_zerg_bot_pro.py`)

¸ÞÀÎ º¿ Å¬·¡½º·Î ¸ðµç ¸Å´ÏÀú¸¦ ÅëÇÕ °ü¸®ÇÕ´Ï´Ù.

**Ã¥ÀÓ:**
- °ÔÀÓ ·çÇÁ ½ÇÇà (`on_step`)
- ¸Å´ÏÀú °£ Åë½Å Á¶À²
- Àü·« ·¹ÀÌ¾î Á¦¾î

**ÁÖ¿ä ¸Þ¼­µå:**
```python
async def on_start(self):
    """°ÔÀÓ ½ÃÀÛ ½Ã ÃÊ±âÈ­"""
    
async def on_step(self, iteration: int):
    """¸Å ÇÁ·¹ÀÓ ½ÇÇà"""
    
async def on_end(self, game_result: Result):
    """°ÔÀÓ Á¾·á ½Ã Á¤¸®"""
```

### 2. Manager System

#### EconomyManager (`economy_manager.py`)
- **¿ªÇÒ**: ÀÚ¿ø °ü¸®, È®Àå, °Ç¹° °Ç¼³
- **Ã¥ÀÓ**:
  - ¹Ì³×¶ö/°¡½º ¼öÁý ÃÖÀûÈ­
  - È®Àå ±âÁö °Ç¼³
  - ÀÏ²Û »ý»ê ¹× ¹èÄ¡

#### ProductionManager (`production_manager.py`)
- **¿ªÇÒ**: À¯´Ö »ý»ê ¹× Å×Å© Æ®¸® °ü¸®
- **Ã¥ÀÓ**:
  - ¶ó¹Ù ±â¹Ý À¯´Ö »ý»ê
  - Å×Å© Æ®¸® ÁøÈ­
  - ºñ»ó »ý»ê ÇÃ·¯½Ã ·ÎÁ÷

#### CombatManager (`combat_manager.py`)
- **¿ªÇÒ**: ÀüÅõ Àü·« ¹× À¯´Ö Á¦¾î
- **Ã¥ÀÓ**:
  - Àû º´·Â ºÐ¼®
  - Àü¼ú ¼±ÅÃ (°ø°Ý/¹æ¾î/È®Àå)
  - ¸¶ÀÌÅ©·Î ÄÁÆ®·Ñ

#### IntelManager (`intel_manager.py`)
- **¿ªÇÒ**: Blackboard ÆÐÅÏ ±¸Çö
- **Ã¥ÀÓ**:
  - Àû Á¤º¸ ¼öÁý ¹× Ä³½Ì
  - Àü·« µ¥ÀÌÅÍ °øÀ¯
  - À§Çù ·¹º§ Æò°¡

#### ScoutingSystem (`scouting_system.py`)
- **¿ªÇÒ**: Á¤Âû ¹× ¸Ê Å½»ö
- **Ã¥ÀÓ**:
  - ´ë±ºÁÖ ¹èÄ¡ ¹× ÀÌµ¿
  - Àû ±âÁö Å½Áö
  - ¸Ê Á¤º¸ ¼öÁý

### 3. Learning System

#### ZergNet (`zerg_net.py`)
- **¿ªÇÒ**: °­È­ÇÐ½À ½Å°æ¸Á
- **Ã¥ÀÓ**:
  - »óÅÂ º¤ÅÍ ÀÔ·Â Ã³¸®
  - Çàµ¿ Á¤Ã¥ Ãâ·Â
  - ¸®ÇÃ·¹ÀÌ ÇÐ½À

#### CurriculumManager (`curriculum_manager.py`)
- **¿ªÇÒ**: Ä¿¸®Å§·³ ÇÐ½À °ü¸®
- **Ã¥ÀÓ**:
  - ³­ÀÌµµ Á¶Àý
  - ÇÐ½À ´Ü°è ÁøÇà

### 4. Self-Healing System

#### GenAISelfHealing (`genai_self_healing.py`)
- **¿ªÇÒ**: AI ±â¹Ý ÀÚµ¿ ¿À·ù ¼öÁ¤
- **Ã¥ÀÓ**:
  - ·±Å¸ÀÓ ¿À·ù °¨Áö
  - Gemini API¸¦ ÅëÇÑ ÄÚµå ºÐ¼®
  - ÀÚµ¿ ÆÐÄ¡ »ý¼º ¹× Àû¿ë

### 5. Monitoring System

#### Dashboard API (`monitoring/dashboard_api.py`)
- **¿ªÇÒ**: FastAPI ±â¹Ý REST API
- **¿£µåÆ÷ÀÎÆ®**:
  - `/api/status` - º¿ »óÅÂ
  - `/api/telemetry` - ÅÚ·¹¸ÞÆ®¸® µ¥ÀÌÅÍ
  - `/api/stats` - Åë°è Á¤º¸

#### Telemetry Logger (`monitoring/telemetry_logger.py`)
- **¿ªÇÒ**: °ÔÀÓ µ¥ÀÌÅÍ ·Î±ë
- **Ã¥ÀÓ**:
  - ½Ç½Ã°£ µ¥ÀÌÅÍ ¼öÁý
  - JSON/CSV ÆÄÀÏ ÀúÀå
  - ¿øÀÚÀû ¾²±â º¸Àå

---

## µ¥ÀÌÅÍ Èå¸§

### 1. °ÔÀÓ ½ÇÇà Èå¸§

```
Game Start
    ¦¢
    ¦§¦¡? Bot.on_start()
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? Initialize Managers
    ¦¢       ¦¢       ¦§¦¡? IntelManager (¸ÕÀú)
    ¦¢       ¦¢       ¦§¦¡? EconomyManager
    ¦¢       ¦¢       ¦§¦¡? ProductionManager
    ¦¢       ¦¢       ¦¦¦¡? CombatManager
    ¦¢       ¦¢
    ¦¢       ¦¦¦¡? Setup Telemetry
    ¦¢
    ¦§¦¡? Game Loop (on_step)
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? IntelManager.update()
    ¦¢       ¦¢       ¦¦¦¡? Collect enemy info
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? EconomyManager.update()
    ¦¢       ¦¢       ¦¦¦¡? Manage resources
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? ProductionManager.update()
    ¦¢       ¦¢       ¦¦¦¡? Produce units
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? CombatManager.update()
    ¦¢       ¦¢       ¦¦¦¡? Control units
    ¦¢       ¦¢
    ¦¢       ¦¦¦¡? TelemetryLogger.save()
    ¦¢
    ¦¦¦¡? Game End (on_end)
            ¦¦¦¡? Save statistics
```

### 2. Self-Healing Èå¸§

```
Runtime Error
    ¦¢
    ¦§¦¡? Exception Caught
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? Collect Traceback
    ¦¢       ¦§¦¡? Collect Source Code
    ¦¢       ¦¦¦¡? Collect Context
    ¦¢
    ¦§¦¡? Send to Gemini API
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? Analyze Error
    ¦¢       ¦§¦¡? Generate Fix
    ¦¢       ¦¦¦¡? Return Patch
    ¦¢
    ¦§¦¡? Apply Patch
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? Backup Original
    ¦¢       ¦§¦¡? Write New Code
    ¦¢       ¦¦¦¡? Reload Module
    ¦¢
    ¦¦¦¡? Resume Execution
```

### 3. Monitoring Èå¸§

```
Bot Execution
    ¦¢
    ¦§¦¡? TelemetryLogger
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? Collect Data (every step)
    ¦¢       ¦§¦¡? Save to JSON/CSV
    ¦¢       ¦¦¦¡? Atomic Write
    ¦¢
    ¦§¦¡? Dashboard API
    ¦¢       ¦¢
    ¦¢       ¦§¦¡? Read Telemetry Files
    ¦¢       ¦§¦¡? Process Data
    ¦¢       ¦¦¦¡? Serve via REST API
    ¦¢
    ¦¦¦¡? Mobile App
            ¦¢
            ¦§¦¡? Poll API
            ¦§¦¡? Update UI
            ¦¦¦¡? Display Metrics
```

---

## ¸ðµâ °£ Åë½Å

### Blackboard ÆÐÅÏ (IntelManager)

IntelManager´Â ¸ðµç ¸Å´ÏÀú°¡ °øÀ¯ÇÏ´Â Á¤º¸ ÀúÀå¼Ò ¿ªÇÒÀ» ÇÕ´Ï´Ù.

```python
# Á¤º¸ ¾²±â
bot.intel_manager.set_enemy_army_composition(composition)
bot.intel_manager.set_threat_level(ThreatLevel.HIGH)

# Á¤º¸ ÀÐ±â
composition = bot.intel_manager.get_enemy_army_composition()
threat = bot.intel_manager.get_threat_level()
```

### ÀÌº¥Æ® ±â¹Ý Åë½Å

¸Å´ÏÀú °£ ÀÌº¥Æ®¸¦ ÅëÇØ Åë½ÅÇÒ ¼ö ÀÖ½À´Ï´Ù.

```python
# ÀÌº¥Æ® ¹ß»ý
bot.intel_manager.on_enemy_detected(enemy_location)

# ÀÌº¥Æ® ¼ö½Å
@event_handler('enemy_detected')
def handle_enemy_detected(location):
    # Àû ÀÀ´ä ·ÎÁ÷
    pass
```

---

## È®Àå °¡´É¼º

### »õ·Î¿î ¸Å´ÏÀú Ãß°¡

1. `BaseManager`¸¦ »ó¼Ó¹Þ´Â Å¬·¡½º »ý¼º
2. `on_start()`, `on_step()` ¸Þ¼­µå ±¸Çö
3. `wicked_zerg_bot_pro.py`¿¡ µî·Ï

```python
class MyNewManager(BaseManager):
    async def on_start(self):
        # ÃÊ±âÈ­ ·ÎÁ÷
        pass
    
    async def on_step(self, iteration: int):
        # ½ÇÇà ·ÎÁ÷
        pass
```

### »õ·Î¿î ÇÐ½À ¾Ë°í¸®Áò Ãß°¡

1. `ZergNet`À» »ó¼Ó¹Þ´Â Å¬·¡½º »ý¼º
2. ³×Æ®¿öÅ© ¾ÆÅ°ÅØÃ³ Á¤ÀÇ
3. ÇÐ½À ·çÇÁ¿¡ ÅëÇÕ

---

## ¼º´É ÃÖÀûÈ­

### ºñµ¿±â Ã³¸®
- ¸ðµç ¸Å´ÏÀú´Â `async/await` ÆÐÅÏ »ç¿ë
- µ¿½Ã ´ÙÁß À¯´Ö Á¦¾î °¡´É

### Ä³½Ì
- IntelManager¿¡¼­ Àû Á¤º¸ Ä³½Ì
- ºÒÇÊ¿äÇÑ Àç°è»ê ¹æÁö

### ¹èÄ¡ Ã³¸®
- À¯´Ö ¸í·ÉÀ» ¹èÄ¡·Î ¹­¾î Ã³¸®
- ³×Æ®¿öÅ© ¿À¹öÇìµå °¨¼Ò

---

## º¸¾È °í·Á»çÇ×

- API Å°´Â È¯°æ º¯¼ö·Î °ü¸®
- `.env` ÆÄÀÏÀº Git¿¡ ÃßÀûµÇÁö ¾ÊÀ½
- ¹Î°¨ÇÑ Á¤º¸´Â `secrets/` Æú´õ¿¡ ÀúÀå

---

## Âü°í ÀÚ·á

- [ÆÄÀÏ ±¸Á¶ ¼³¸í](wicked_zerg_challenger/¼³¸í¼­/FILE_STRUCTURE.md)
- [½ÇÇà Èå¸§ ¼³¸í](wicked_zerg_challenger/docs/COMPLETE_EXECUTION_FLOW.md)
- [ÄÚµå ¿¹½Ã](wicked_zerg_challenger/¼³¸í¼­/)
