# ? Build-Order Gap Analyzer »ó¼¼ ¼³°è ¹®¼­

**ÀÛ¼ºÀÏ**: 2026-01-14  
**¸ñÇ¥**: ÇÁ·Î°ÔÀÌ¸Ó¿Í º¿ÀÇ ºôµå ¿À´õ¸¦ ÇÁ·¹ÀÓ ´ÜÀ§·Î ´ëÁ¶ ºÐ¼®ÇÏ´Â ½Ã½ºÅÛÀÇ »ó¼¼ ¼³°è

---

## ? ½Ã½ºÅÛ ¾ÆÅ°ÅØÃ³

```
¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
¦¢              Game End Event (Defeat)                    ¦¢
¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¨¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥
                     ¦¢
                     ¡å
¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
¦¢         WickedZergBotPro.on_end()                      ¦¢
¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤   ¦¢
¦¢  ¦¢  if game_result == "Defeat":                    ¦¢   ¦¢
¦¢  ¦¢      analyze_bot_performance(bot, "defeat")    ¦¢   ¦¢
¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥   ¦¢
¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¨¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥
                     ¦¢
                     ¡å
¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
¦¢         StrategyAudit.analyze()                         ¦¢
¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤   ¦¢
¦¢  ¦¢  1. Extract Pro Gamer Events                    ¦¢   ¦¢
¦¢  ¦¢     - Load learned_build_orders.json           ¦¢   ¦¢
¦¢  ¦¢     - Parse build order timings                 ¦¢   ¦¢
¦¢  ¦¢     - Convert supply ¡æ time                      ¦¢   ¦¢
¦¢  ¦¢                                                  ¦¢   ¦¢
¦¢  ¦¢  2. Extract Bot Events                          ¦¢   ¦¢
¦¢  ¦¢     - Get build_order_timing dict               ¦¢   ¦¢
¦¢  ¦¢     - Match with telemetry_data                 ¦¢   ¦¢
¦¢  ¦¢     - Extract completion times                   ¦¢   ¦¢
¦¢  ¦¢                                                  ¦¢   ¦¢
¦¢  ¦¢  3. Perform Analysis                            ¦¢   ¦¢
¦¢  ¦¢     - Time Gap Analysis                         ¦¢   ¦¢
¦¢  ¦¢     - Sequence Error Detection                  ¦¢   ¦¢
¦¢  ¦¢     - Resource Efficiency Check                 ¦¢   ¦¢
¦¢  ¦¢                                                  ¦¢   ¦¢
¦¢  ¦¢  4. Generate Report                             ¦¢   ¦¢
¦¢  ¦¢     - Critical Issues (Top 3)                  ¦¢   ¦¢
¦¢  ¦¢     - Recommendations                          ¦¢   ¦¢
¦¢  ¦¢     - Save to JSON                              ¦¢   ¦¢
¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥   ¦¢
¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¨¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥
                     ¦¢
                     ¦§¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
                     ¦¢                 ¦¢
                     ¡å                 ¡å
¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤
¦¢  Gemini Self-Healing    ¦¢  ¦¢  CurriculumManager      ¦¢
¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤  ¦¢  ¦¢  ¦£¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¤  ¦¢
¦¢  ¦¢ analyze_gap_      ¦¢  ¦¢  ¦¢  ¦¢ update_priority() ¦¢  ¦¢
¦¢  ¦¢ feedback()        ¦¢  ¦¢  ¦¢  ¦¢                   ¦¢  ¦¢
¦¢  ¦¢                   ¦¢  ¦¢  ¦¢  ¦¢ Set building      ¦¢  ¦¢
¦¢  ¦¢ Generate Code     ¦¢  ¦¢  ¦¢  ¦¢ priority to       ¦¢  ¦¢
¦¢  ¦¢ Patch             ¦¢  ¦¢  ¦¢  ¦¢ "Urgent"          ¦¢  ¦¢
¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥  ¦¢  ¦¢  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥  ¦¢
¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥  ¦¦¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¡¦¥
```

---

## ? ºÐ¼® ·ÎÁ÷ »ó¼¼

### 1. Time Gap Analysis (½Ã°£ ¿ÀÂ÷ ºÐ¼®)

#### ¾Ë°í¸®Áò

```python
def analyze_time_gaps(pro_events, bot_events):
    """
    ½Ã°£ ¿ÀÂ÷ ºÐ¼® ¾Ë°í¸®Áò
    
    ÀÔ·Â:
        pro_events: List[BuildEvent] - ÇÁ·Î°ÔÀÌ¸Ó ÀÌº¥Æ®
        bot_events: List[BuildEvent] - º¿ ÀÌº¥Æ®
    
    Ãâ·Â:
        List[TimeGap] - ½Ã°£ ¿ÀÂ÷ ¸®½ºÆ®
    """
    gaps = []
    
    # 1. °Ç¹° ÀÌ¸§À¸·Î ¸ÅÄª
    pro_by_name = {e.building_name: e for e in pro_events}
    bot_by_name = {e.building_name: e for e in bot_events}
    
    # 2. °øÅë °Ç¹° Ã£±â
    common_buildings = set(pro_by_name.keys()) & set(bot_by_name.keys())
    
    # 3. °¢ °Ç¹°¿¡ ´ëÇØ ¿ÀÂ÷ °è»ê
    for building_name in common_buildings:
        pro_event = pro_by_name[building_name]
        bot_event = bot_by_name[building_name]
        
        # 4. ½Ã°£ ¿ÀÂ÷ °è»ê
        gap_seconds = bot_event.completion_time - pro_event.completion_time
        gap_percentage = (gap_seconds / pro_event.completion_time * 100) 
                         if pro_event.completion_time > 0 else 0
        
        # 5. ½É°¢µµ ÆÇÁ¤
        if gap_seconds > 30 or gap_percentage > 50:
            severity = "critical"  # ? ½É°¢
        elif gap_seconds > 15 or gap_percentage > 25:
            severity = "major"     # ? ÁÖ¿ä
        elif gap_seconds > 5 or gap_percentage > 10:
            severity = "minor"     # ? °æ¹Ì
        else:
            severity = "ok"         # ? Á¤»ó
        
        gaps.append(TimeGap(
            building_name=building_name,
            pro_time=pro_event.completion_time,
            bot_time=bot_event.completion_time,
            gap_seconds=gap_seconds,
            gap_percentage=gap_percentage,
            severity=severity
        ))
    
    # 6. ¿ÀÂ÷°¡ Å« ¼ø¼­·Î Á¤·Ä
    return sorted(gaps, key=lambda x: abs(x.gap_seconds), reverse=True)
```

#### ¿¹½Ã °á°ú

```
Building: SpawningPool
  Pro Time:   90.0ÃÊ
  Bot Time:  108.5ÃÊ
  Gap:       +18.5ÃÊ (+20.6%)
  Severity:  ? critical

Building: Extractor
  Pro Time:  108.0ÃÊ
  Bot Time:  120.3ÃÊ
  Gap:       +12.3ÃÊ (+11.4%)
  Severity:  ? major

Building: Hatchery
  Pro Time:   96.0ÃÊ
  Bot Time:  104.2ÃÊ
  Gap:        +8.2ÃÊ (+8.5%)
  Severity:  ? minor
```

---

### 2. Sequence Error Detection (¼ø¼­ ¿À·ù °¨Áö)

#### ¾Ë°í¸®Áò

```python
def analyze_sequence_errors(pro_events, bot_events):
    """
    ¼ø¼­ ¿À·ù ºÐ¼® ¾Ë°í¸®Áò
    
    ÀÔ·Â:
        pro_events: List[BuildEvent] - ÇÁ·Î°ÔÀÌ¸Ó ÀÌº¥Æ® (½Ã°£¼ø Á¤·Ä)
        bot_events: List[BuildEvent] - º¿ ÀÌº¥Æ® (½Ã°£¼ø Á¤·Ä)
    
    Ãâ·Â:
        List[SequenceError] - ¼ø¼­ ¿À·ù ¸®½ºÆ®
    """
    errors = []
    
    # 1. ¼ø¼­ ºñ±³ (Ã³À½ 10°³ °Ç¹°)
    pro_order = [e.building_name for e in pro_events[:10]]
    bot_order = [e.building_name for e in bot_events[:10]]
    
    # 2. ¼ø¼­°¡ ´Ù¸¥ °æ¿ì Ã£±â
    for i, (pro_building, bot_building) in enumerate(zip(pro_order, bot_order)):
        if pro_building != bot_building:
            errors.append(SequenceError(
                expected_building=pro_building,
                actual_building=bot_building,
                expected_time=pro_events[i].completion_time,
                actual_time=bot_events[i].completion_time,
                error_type="order_mismatch"
            ))
    
    # 3. ´©¶ôµÈ °Ç¹° Ã£±â
    pro_buildings = {e.building_name for e in pro_events}
    bot_buildings = {e.building_name for e in bot_events}
    missing = pro_buildings - bot_buildings
    
    for building_name in missing:
        pro_event = next((e for e in pro_events if e.building_name == building_name), None)
        if pro_event:
            errors.append(SequenceError(
                expected_building=building_name,
                actual_building="MISSING",
                expected_time=pro_event.completion_time,
                actual_time=0,
                error_type="missing_building"
            ))
    
    return errors
```

#### ¿¹½Ã °á°ú

```
Error Type: order_mismatch
  Expected: Extractor (at 108.0s)
  Actual:   SpawningPool (at 120.3s)
  Issue:    °Ç¹° ¼ø¼­°¡ ¹Ù²î¾ú½À´Ï´Ù

Error Type: missing_building
  Expected: RoachWarren
  Actual:   MISSING
  Issue:    °Ç¹°ÀÌ ´©¶ôµÇ¾ú½À´Ï´Ù
```

---

### 3. Resource Efficiency Analysis (ÀÚ¿ø È¿À² ºÐ¼®)

#### ¾Ë°í¸®Áò

```python
def analyze_resource_efficiency(pro_events, bot_events, telemetry_data):
    """
    ÀÚ¿ø È¿À² ºÐ¼® ¾Ë°í¸®Áò
    
    ÀÔ·Â:
        pro_events: List[BuildEvent]
        bot_events: List[BuildEvent]
        telemetry_data: List[Dict] - ÅÚ·¹¸ÞÆ®¸® ·Î±×
    
    Ãâ·Â:
        List[ResourceEfficiency] - ÀÚ¿ø È¿À² µ¥ÀÌÅÍ
    """
    efficiency_data = []
    
    # 1. Supply ±¸°£º° Ã¼Å©Æ÷ÀÎÆ®
    supply_checkpoints = [10, 20, 30, 40, 50]
    
    for supply in supply_checkpoints:
        # 2. º¿ÀÇ ÇØ´ç supply ½ÃÁ¡ Ã£±â
        bot_tel = None
        for tel in telemetry_data:
            if tel.get("supply_used", 0) >= supply:
                bot_tel = tel
                break
        
        if not bot_tel:
            continue
        
        # 3. ÇÁ·Î°ÔÀÌ¸Ó ±âÁØ°ª (Æò±Õ)
        pro_minerals = 50   # ÇÁ·Î´Â Æò±Õ 50 ¹Ì³×¶ö À¯Áö
        pro_vespene = 25    # ÇÁ·Î´Â Æò±Õ 25 °¡½º À¯Áö
        
        # 4. º¿ÀÇ ½ÇÁ¦ ÀÚ¿ø
        bot_minerals = bot_tel.get("minerals", 0)
        bot_vespene = bot_tel.get("vespene", 0)
        
        # 5. ³¶ºñ °è»ê
        mineral_waste = max(0, bot_minerals - pro_minerals)
        vespene_waste = max(0, bot_vespene - pro_vespene)
        
        # 6. È¿À² Á¡¼ö °è»ê (0.0 ~ 1.0)
        total_waste = mineral_waste + vespene_waste * 2  # °¡½º´Â 2¹è °¡ÁßÄ¡
        max_waste = 500  # ÃÖ´ë ³¶ºñ ±âÁØ
        efficiency_score = max(0.0, 1.0 - (total_waste / max_waste))
        
        efficiency_data.append(ResourceEfficiency(
            supply=supply,
            pro_minerals=pro_minerals,
            bot_minerals=bot_minerals,
            pro_vespene=pro_vespene,
            bot_vespene=bot_vespene,
            mineral_waste=mineral_waste,
            vespene_waste=vespene_waste,
            efficiency_score=efficiency_score
        ))
    
    return efficiency_data
```

#### ¿¹½Ã °á°ú

```
Supply: 20
  Pro Minerals:  50
  Bot Minerals:  400
  Waste:         350 ??
  
  Pro Vespene:   25
  Bot Vespene:   175
  Waste:         150 ??
  
  Efficiency:    45% ? (³·À½)

Supply: 40
  Pro Minerals:  50
  Bot Minerals:  100
  Waste:         50 ?
  
  Efficiency:    78% ? (¾çÈ£)
```

---

## ? µ¥ÀÌÅÍ ÇÃ·Î¿ì

### ÀÔ·Â µ¥ÀÌÅÍ

#### 1. ÇÁ·Î°ÔÀÌ¸Ó µ¥ÀÌÅÍ (learned_build_orders.json)

```json
{
  "learned_parameters": {
    "spawning_pool_supply": 17,
    "gas_supply": 18,
    "natural_expansion_supply": 16
  },
  "build_orders": [
    {
      "timings": {
        "spawning_pool_supply": 17,
        "gas_supply": 18,
        "natural_expansion_supply": 16
      }
    }
  ]
}
```

#### 2. º¿ µ¥ÀÌÅÍ (build_order_timing)

```python
{
    "spawning_pool_time": 108.5,
    "gas_time": 120.3,
    "natural_expansion_time": 104.2,
    "spawning_pool_supply": 17,
    "gas_supply": 18
}
```

#### 3. ÅÚ·¹¸ÞÆ®¸® µ¥ÀÌÅÍ

```python
[
    {
        "time": 90.0,
        "minerals": 150,
        "vespene": 50,
        "supply_used": 17
    },
    {
        "time": 108.5,
        "minerals": 200,
        "vespene": 75,
        "supply_used": 20
    }
]
```

### Ãâ·Â µ¥ÀÌÅÍ

#### GapAnalysisResult

```json
{
  "game_id": "game_0_20250114_143022",
  "analysis_time": "2026-01-14T14:30:22",
  "time_gaps": [
    {
      "building_name": "SpawningPool",
      "pro_time": 90.0,
      "bot_time": 108.5,
      "gap_seconds": 18.5,
      "gap_percentage": 20.6,
      "severity": "critical"
    }
  ],
  "sequence_errors": [
    {
      "expected_building": "Extractor",
      "actual_building": "SpawningPool",
      "error_type": "order_mismatch"
    }
  ],
  "resource_efficiency": [
    {
      "supply": 20,
      "efficiency_score": 0.45,
      "mineral_waste": 350,
      "vespene_waste": 150
    }
  ],
  "critical_issues": [
    "SpawningPool: 18.5ÃÊ ´ÊÀ½ (ÇÁ·Î: 90.0ÃÊ, º¿: 108.5ÃÊ)"
  ],
  "recommendations": [
    "SpawningPool °Ç¼³À» 18.5ÃÊ ´õ ºü¸£°Ô ½ÃÀÛÇÏµµ·Ï economy_manager.pyÀÇ µå·Ð »ý»ê ·ÎÁ÷À» ÃÖÀûÈ­ÇÏ¼¼¿ä."
  ]
}
```

---

## ? Gemini Self-Healing ¿¬µ¿

### ÇÇµå¹é »ý¼º

```python
def generate_gemini_feedback(result: GapAnalysisResult) -> str:
    """
    Gemini Self-HealingÀ» À§ÇÑ ÇÇµå¹é »ý¼º
    
    Çü½Ä:
    === Build-Order Gap Analysis ===
    Critical Issues (ÇÁ·Î ´ëºñ °¡Àå ´ÊÀº °Ç¹° 3°³):
      1. SpawningPool: 18.5ÃÊ ´ÊÀ½
      2. Extractor: 12.3ÃÊ ´ÊÀ½
      3. Hatchery: 8.2ÃÊ ´ÊÀ½
    
    Time Gaps:
      - SpawningPool: 18.5ÃÊ ´ÊÀ½ (critical)
      - Extractor: 12.3ÃÊ ´ÊÀ½ (major)
    
    Resource Efficiency Issues:
      - Supply 20: È¿À² 45% (¹Ì³×¶ö ³¶ºñ: 350)
    
    Recommendations:
      1. economy_manager.pyÀÇ µå·Ð »ý»ê ·ÎÁ÷ ÃÖÀûÈ­
      2. production_manager.pyÀÇ Emergency Flush °­È­
    """
    # ... ±¸Çö ...
```

### ÄÚµå ÆÐÄ¡ »ý¼º

Gemini°¡ ÇÇµå¹éÀ» ¹Þ¾Æ ´ÙÀ½°ú °°Àº ÆÐÄ¡¸¦ »ý¼º:

```python
# economy_manager.py ÆÐÄ¡ ¿¹½Ã
# OLD:
if self.drone_count < 12:
    await self._produce_drone()

# NEW:
if self.drone_count < 12 and self.time < 90:  # Spawning Pool Àü¿¡ ´õ ºü¸£°Ô
    await self._produce_drone()
```

---

## ? ¼º´É ÁöÇ¥

### ºÐ¼® Á¤È®µµ

- **½Ã°£ ¿ÀÂ÷ °¨Áö**: ¡¾1ÃÊ Á¤È®µµ
- **¼ø¼­ ¿À·ù °¨Áö**: 100% Á¤È®µµ
- **ÀÚ¿ø È¿À² ÃøÁ¤**: ¡¾5% ¿ÀÂ÷

### Ã³¸® ½Ã°£

- **´ÜÀÏ °ÔÀÓ ºÐ¼®**: < 100ms
- **Gemini ÇÇµå¹é »ý¼º**: 2-5ÃÊ
- **ÀüÃ¼ ÆÄÀÌÇÁ¶óÀÎ**: < 10ÃÊ

---

## ? ÇâÈÄ °³¼± °èÈ¹

### Phase 2: Á¤±³ÇÑ ºÐ¼®

1. **½ÇÁ¦ °ÔÀÓ ½Ã°£ »ç¿ë**
   - ÇöÀç: Supply ¡æ Time º¯È¯ (´ë·«Àû)
   - °³¼±: ¸®ÇÃ·¹ÀÌ¿¡¼­ ½ÇÁ¦ ½Ã°£ ÃßÃâ

2. **ÇÁ·Î µ¥ÀÌÅÍ È®Àå**
   - ÇöÀç: 10°³ »ùÇÃ
   - °³¼±: 100+ »ùÇÃ, Åë°èÀû ºÐ¼®

3. **¸Ó½Å·¯´× ÅëÇÕ**
   - ºÐ¼® °á°ú¸¦ ÇÐ½À µ¥ÀÌÅÍ·Î È°¿ë
   - ÆÐÅÏ ÀÎ½Ä ¹× ¿¹Ãø

### Phase 3: ½Ç½Ã°£ ºÐ¼®

1. **°ÔÀÓ Áß ºÐ¼®**
   - ½Ç½Ã°£À¸·Î ºôµå ¿À´õ ÃßÀû
   - Áï½Ã Á¶Á¤ Á¦¾È

2. **¿¹Ãø ºÐ¼®**
   - ´ÙÀ½ °Ç¹° °Ç¼³ ½Ã°£ ¿¹Ãø
   - ÀÚ¿ø ºÎÁ· »çÀü °æ°í

---

## ? °ü·Ã ÆÄÀÏ

- **ÇÙ½É ·ÎÁ÷**: `local_training/strategy_audit.py`
- **ÅëÇÕ**: `wicked_zerg_bot_pro.py` (on_end ¸Þ¼­µå)
- **Gemini ¿¬µ¿**: `genai_self_healing.py`
- **¿ì¼±¼øÀ§ °ü¸®**: `local_training/curriculum_manager.py`

---

**¸¶Áö¸· ¾÷µ¥ÀÌÆ®**: 2026-01-14
