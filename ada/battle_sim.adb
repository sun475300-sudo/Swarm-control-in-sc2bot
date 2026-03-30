-- Wicked Zerg - Battle Simulation
-- Phase 134: Ada

with Ada.Text_IO; use Ada.Text_IO;
with Ada.Numerics.Generic_Elementary_Functions;

procedure Battle_Sim is
   
   type Battle_Unit is record
      Unit_Type : Integer;
      Health    : Float;
      Damage    : Float;
      Armor     : Float;
      Pos_X     : Float;
      Pos_Y     : Float;
   end record;
   
   package Math is new Ada.Numerics.Generic_Elementary_Functions(Float);
   use Math;
   
   function Calculate_Swarm_Damage (Count : Integer) return Integer is
   begin
      return Count * 5;
   end Calculate_Swarm_Damage;
   
   function Unit_Strength (Health, Damage, Armor : Float) return Float is
      Effective : Float;
   begin
      Effective := Damage * Health / 100.0;
      return Effective * (1.0 - Armor * 0.01);
   end Unit_Strength;
   
begin
   Put_Line("Battle Simulation Initialized - Ada");
end Battle_Sim;
