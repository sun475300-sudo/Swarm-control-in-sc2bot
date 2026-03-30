/**
 * SC2 Zerg AI Bot — CUDA Combat Simulation Kernel
 *
 * Each CUDA thread simulates one full battle between two unit groups
 * (e.g. Zergling swarm vs Terran Marines) in parallel.
 * Focused-fire targeting: attackers always hit the lowest-HP defender.
 */

#include <cuda_runtime.h>
#include <device_launch_parameters.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_UNITS      32    // max units per side per battle
#define DEAD_THRESHOLD 0     // unit dies when HP <= 0

// -----------------------------------------------------------------------
// Structs
// -----------------------------------------------------------------------

struct UnitState {
    int hp[MAX_UNITS];
    int attack[MAX_UNITS];
    int count;
};

struct BattleInput {
    UnitState side_a;   // Zerg attackers
    UnitState side_b;   // Enemy defenders
};

struct BattleResult {
    int winner;              // 0 = side_a, 1 = side_b, -1 = draw
    int rounds;
    int survivors_a;
    int survivors_b;
    int total_dmg_a;         // damage dealt by side_a
    int total_dmg_b;
};

// -----------------------------------------------------------------------
// Device helper: find index of lowest-HP alive unit
// -----------------------------------------------------------------------
__device__ int findFocusTarget(const int* hp, int count) {
    int best = -1;
    int bestHp = INT_MAX;
    for (int i = 0; i < count; i++) {
        if (hp[i] > DEAD_THRESHOLD && hp[i] < bestHp) {
            bestHp = hp[i];
            best   = i;
        }
    }
    return best;
}

__device__ int countAlive(const int* hp, int count) {
    int alive = 0;
    for (int i = 0; i < count; i++)
        if (hp[i] > DEAD_THRESHOLD) alive++;
    return alive;
}

// -----------------------------------------------------------------------
// Main combat kernel — one thread = one battle
// -----------------------------------------------------------------------
__global__ void simulateCombat(
    const BattleInput*  inputs,
    BattleResult*       results,
    int                 num_battles,
    int*                win_counter_a,   // atomic win tally
    int*                win_counter_b
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    if (tid >= num_battles) return;

    // Local copy of unit HP (registers / local mem)
    int hp_a[MAX_UNITS], atk_a[MAX_UNITS];
    int hp_b[MAX_UNITS], atk_b[MAX_UNITS];
    int cnt_a = inputs[tid].side_a.count;
    int cnt_b = inputs[tid].side_b.count;

    for (int i = 0; i < cnt_a; i++) {
        hp_a[i]  = inputs[tid].side_a.hp[i];
        atk_a[i] = inputs[tid].side_a.attack[i];
    }
    for (int i = 0; i < cnt_b; i++) {
        hp_b[i]  = inputs[tid].side_b.hp[i];
        atk_b[i] = inputs[tid].side_b.attack[i];
    }

    int rounds    = 0;
    int dmg_a     = 0;
    int dmg_b     = 0;
    const int MAX_ROUNDS = 500;

    // Combat loop — simultaneous attack each round
    while (rounds < MAX_ROUNDS) {
        int alive_a = countAlive(hp_a, cnt_a);
        int alive_b = countAlive(hp_b, cnt_b);
        if (alive_a == 0 || alive_b == 0) break;

        // Side A focuses lowest-HP enemy
        int target_b = findFocusTarget(hp_b, cnt_b);
        for (int i = 0; i < cnt_a; i++) {
            if (hp_a[i] > DEAD_THRESHOLD && target_b >= 0) {
                int dmg = atk_a[i];
                hp_b[target_b] -= dmg;
                dmg_a          += dmg;
                if (hp_b[target_b] <= DEAD_THRESHOLD)
                    target_b = findFocusTarget(hp_b, cnt_b);
            }
        }

        // Side B focuses lowest-HP attacker
        int target_a = findFocusTarget(hp_a, cnt_a);
        for (int i = 0; i < cnt_b; i++) {
            if (hp_b[i] > DEAD_THRESHOLD && target_a >= 0) {
                int dmg = atk_b[i];
                hp_a[target_a] -= dmg;
                dmg_b          += dmg;
                if (hp_a[target_a] <= DEAD_THRESHOLD)
                    target_a = findFocusTarget(hp_a, cnt_a);
            }
        }
        rounds++;
    }

    int final_a = countAlive(hp_a, cnt_a);
    int final_b = countAlive(hp_b, cnt_b);

    BattleResult res;
    res.rounds       = rounds;
    res.survivors_a  = final_a;
    res.survivors_b  = final_b;
    res.total_dmg_a  = dmg_a;
    res.total_dmg_b  = dmg_b;

    if (final_a > 0 && final_b == 0) {
        res.winner = 0;
        atomicAdd(win_counter_a, 1);
    } else if (final_b > 0 && final_a == 0) {
        res.winner = 1;
        atomicAdd(win_counter_b, 1);
    } else {
        res.winner = -1;
    }
    results[tid] = res;
}

// -----------------------------------------------------------------------
// Host wrapper
// -----------------------------------------------------------------------
void runCombatSimulation(
    const BattleInput* h_inputs,
    BattleResult*      h_results,
    int                num_battles
) {
    size_t inSize  = num_battles * sizeof(BattleInput);
    size_t outSize = num_battles * sizeof(BattleResult);

    BattleInput*  d_inputs;
    BattleResult* d_results;
    int*          d_wins_a;
    int*          d_wins_b;

    cudaMalloc(&d_inputs,  inSize);
    cudaMalloc(&d_results, outSize);
    cudaMalloc(&d_wins_a,  sizeof(int));
    cudaMalloc(&d_wins_b,  sizeof(int));
    cudaMemset(d_wins_a, 0, sizeof(int));
    cudaMemset(d_wins_b, 0, sizeof(int));

    cudaMemcpy(d_inputs, h_inputs, inSize, cudaMemcpyHostToDevice);

    int threads = 256;
    int blocks  = (num_battles + threads - 1) / threads;
    simulateCombat<<<blocks, threads>>>(d_inputs, d_results, num_battles, d_wins_a, d_wins_b);
    cudaDeviceSynchronize();

    cudaMemcpy(h_results, d_results, outSize, cudaMemcpyDeviceToHost);

    int wins_a = 0, wins_b = 0;
    cudaMemcpy(&wins_a, d_wins_a, sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(&wins_b, d_wins_b, sizeof(int), cudaMemcpyDeviceToHost);

    printf("[CUDA] Battles: %d | Zerg wins: %d | Enemy wins: %d\n",
           num_battles, wins_a, wins_b);

    cudaFree(d_inputs);
    cudaFree(d_results);
    cudaFree(d_wins_a);
    cudaFree(d_wins_b);
}
