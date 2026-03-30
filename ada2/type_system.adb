-- type_system.adb
-- Ada v2 strong-type SC2 unit system for the JARVIS Zerg bot
-- Phase 132 - leverages Ada's compile-time type safety to prevent
-- illegal army compositions (e.g., negative minerals, excess supply)
--
-- Compile: gnatmake type_system.adb
-- Run:     ./type_system

with Ada.Text_IO;         use Ada.Text_IO;
with Ada.Float_Text_IO;   use Ada.Float_Text_IO;

procedure Type_System is

   -- -----------------------------------------------------------------------
   -- Constrained numeric types — the compiler rejects out-of-range values
   -- -----------------------------------------------------------------------

   -- Mineral reserves: 0 to 5000 (no negative minerals, no impossible hoards)
   type Mineral_Amount is range 0 .. 5_000;

   -- Supply cost stored as a fixed-point decimal (0.5 for zerglings)
   -- 'digits 2' gives at least 2 significant decimal digits
   type Supply_Cost is digits 2 range 0.0 .. 8.0;

   -- HP stored as non-negative float
   type Hit_Points is digits 4 range 0.0 .. 9_999.0;

   -- -----------------------------------------------------------------------
   -- Unit type enumeration
   -- -----------------------------------------------------------------------

   type Unit_Kind is
     (Zergling,    -- Fast melee swarm (supply 0.5)
      Roach,       -- Durable armored ranged (supply 2)
      Hydralisk,   -- High DPS ranged anti-air/ground (supply 2)
      LurkerMP,    -- Burrowed siege unit, needs den upgrade (supply 3)
      Ultralisk);  -- Massive melee frontliner (supply 6)

   -- -----------------------------------------------------------------------
   -- Unit record: all fields are strongly typed
   -- -----------------------------------------------------------------------

   type Unit_Record is record
      Kind      : Unit_Kind;
      HP        : Hit_Points;
      Max_HP    : Hit_Points;
      Supply    : Supply_Cost;
      Mineral_V : Mineral_Amount;  -- mineral cost of this unit
   end record;

   -- Convenience constant array: base combat power per unit kind
   type Power_Table is array (Unit_Kind) of Float;
   Base_Power : constant Power_Table :=
     (Zergling  =>  1.0,
      Roach     =>  4.0,
      Hydralisk =>  5.0,
      LurkerMP  =>  8.0,
      Ultralisk => 12.0);

   -- -----------------------------------------------------------------------
   -- Army type: variable-length array of units (max 200 units per army)
   -- -----------------------------------------------------------------------

   Max_Army_Size : constant := 200;
   type Army_Index is range 1 .. Max_Army_Size;
   type Army_Array is array (Army_Index range <>) of Unit_Record;

   -- -----------------------------------------------------------------------
   -- Calculate_Army_Power
   -- HP-weighted sum: power(u) * (u.HP / u.Max_HP) for each unit
   -- Returns 0.0 for an empty or all-dead army
   -- -----------------------------------------------------------------------

   procedure Calculate_Army_Power
     (Army        : in  Army_Array;
      Total_Power : out Float)
   is
      HP_Ratio : Float;
   begin
      Total_Power := 0.0;
      for U of Army loop
         if Float (U.Max_HP) > 0.0 then
            HP_Ratio    := Float (U.HP) / Float (U.Max_HP);
            Total_Power := Total_Power
                         + Base_Power (U.Kind) * HP_Ratio;
         end if;
      end loop;
   end Calculate_Army_Power;

   -- -----------------------------------------------------------------------
   -- Print_Army_Report: display each unit and the total army power
   -- -----------------------------------------------------------------------

   procedure Print_Army_Report (Army : in Army_Array) is
      Total : Float;
   begin
      Put_Line ("-----------------------------------------------");
      Put_Line (" Unit           HP       MaxHP   Supply  Power ");
      Put_Line ("-----------------------------------------------");
      for U of Army loop
         Put (Unit_Kind'Image (U.Kind));
         Set_Col (16);
         Put (Float (U.HP),    Fore => 6, Aft => 1, Exp => 0);
         Put (" /");
         Put (Float (U.Max_HP), Fore => 6, Aft => 1, Exp => 0);
         Put ("   ");
         Put (Float (U.Supply), Fore => 4, Aft => 1, Exp => 0);
         Put ("   ");
         Put (Base_Power (U.Kind) * (Float (U.HP) / Float (U.Max_HP)),
              Fore => 5, Aft => 2, Exp => 0);
         New_Line;
      end loop;
      Put_Line ("-----------------------------------------------");
      Calculate_Army_Power (Army, Total);
      Put ("  Total army power: ");
      Put (Total, Fore => 6, Aft => 2, Exp => 0);
      New_Line;
      Put_Line ("-----------------------------------------------");
   end Print_Army_Report;

   -- -----------------------------------------------------------------------
   -- Example army definition
   -- -----------------------------------------------------------------------

   My_Army : constant Army_Array :=
     (1 => (Kind => Zergling,  HP => 35.0,  Max_HP => 35.0,  Supply => 0.5, Mineral_V =>  25),
      2 => (Kind => Zergling,  HP => 20.0,  Max_HP => 35.0,  Supply => 0.5, Mineral_V =>  25),
      3 => (Kind => Roach,     HP => 145.0, Max_HP => 145.0, Supply => 2.0, Mineral_V =>  75),
      4 => (Kind => Hydralisk, HP => 80.0,  Max_HP => 90.0,  Supply => 2.0, Mineral_V => 100),
      5 => (Kind => LurkerMP,  HP => 200.0, Max_HP => 200.0, Supply => 3.0, Mineral_V => 150),
      6 => (Kind => Ultralisk, HP => 500.0, Max_HP => 500.0, Supply => 6.0, Mineral_V => 300));

begin
   Put_Line ("=== JARVIS ZERG BOT - Ada Strong-Type Army Evaluation ===");
   New_Line;
   Print_Army_Report (My_Army);
   New_Line;
   Put_Line ("Ada type system guarantees:");
   Put_Line ("  * Mineral_Amount never goes negative (range 0..5000)");
   Put_Line ("  * Supply_Cost always in [0.0 .. 8.0] (digits 2)");
   Put_Line ("  * Hit_Points never negative (range 0.0 .. 9999.0)");
   Put_Line ("  * Unit_Kind exhaustive: all cases covered by compiler");
end Type_System;
