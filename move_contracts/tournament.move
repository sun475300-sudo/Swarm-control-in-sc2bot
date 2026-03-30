/// SC2 Zerg AI Bot — Aptos Move tournament management module.
/// Handles player registration, match result submission, and ranking queries.
module sc2_bot::tournament {

    use std::signer;
    use std::vector;
    use aptos_framework::timestamp;
    use aptos_framework::account;

    // -----------------------------------------------------------------------
    // Constants
    // -----------------------------------------------------------------------

    const E_ALREADY_REGISTERED: u64 = 1;
    const E_NOT_REGISTERED:     u64 = 2;
    const E_INVALID_RESULT:     u64 = 3;
    const BASE_ELO:             u64 = 1200;
    const K_FACTOR:             u64 = 32;

    // -----------------------------------------------------------------------
    // Structs
    // -----------------------------------------------------------------------

    struct PlayerStats has store, copy, drop {
        addr:      address,
        wins:      u64,
        losses:    u64,
        elo:       u64,
        joined_at: u64,
    }

    struct TournamentTable has key, store {
        players:      vector<PlayerStats>,
        match_count:  u64,
    }

    // -----------------------------------------------------------------------
    // Initialization (called once by contract deployer)
    // -----------------------------------------------------------------------

    public fun initialize(admin: &signer) {
        let table = TournamentTable {
            players:     vector::empty<PlayerStats>(),
            match_count: 0,
        };
        move_to(admin, table);
    }

    // -----------------------------------------------------------------------
    // Register a new player
    // -----------------------------------------------------------------------

    public fun register(player: &signer, table_owner: address) acquires TournamentTable {
        let addr = signer::address_of(player);
        let table = borrow_global_mut<TournamentTable>(table_owner);

        // Ensure not already registered
        let len = vector::length(&table.players);
        let i   = 0u64;
        while (i < len) {
            let p = vector::borrow(&table.players, i);
            assert!(p.addr != addr, E_ALREADY_REGISTERED);
            i = i + 1;
        };

        let stats = PlayerStats {
            addr,
            wins:      0,
            losses:    0,
            elo:       BASE_ELO,
            joined_at: timestamp::now_seconds(),
        };
        vector::push_back(&mut table.players, stats);
    }

    // -----------------------------------------------------------------------
    // Submit a match result (winner_addr beat loser_addr)
    // -----------------------------------------------------------------------

    public fun submit_result(
        _submitter:   &signer,
        table_owner:  address,
        winner_addr:  address,
        loser_addr:   address,
    ) acquires TournamentTable {
        let table = borrow_global_mut<TournamentTable>(table_owner);
        let len   = vector::length(&table.players);

        let wi = len; // winner index sentinel
        let li = len; // loser index sentinel
        let i  = 0u64;
        while (i < len) {
            let p = vector::borrow(&table.players, i);
            if (p.addr == winner_addr) { wi = i; };
            if (p.addr == loser_addr)  { li = i; };
            i = i + 1;
        };
        assert!(wi < len && li < len, E_NOT_REGISTERED);

        // Simple fixed ELO delta
        let winner = vector::borrow_mut(&mut table.players, wi);
        winner.wins = winner.wins + 1;
        winner.elo  = winner.elo + K_FACTOR;

        let loser = vector::borrow_mut(&mut table.players, li);
        loser.losses = loser.losses + 1;
        if (loser.elo > K_FACTOR) {
            loser.elo = loser.elo - K_FACTOR;
        } else {
            loser.elo = 0;
        };

        table.match_count = table.match_count + 1;
    }

    // -----------------------------------------------------------------------
    // Get ranking — returns a copy of the player list sorted by ELO desc
    // -----------------------------------------------------------------------

    public fun get_ranking(table_owner: address): vector<PlayerStats> acquires TournamentTable {
        let table = borrow_global<TournamentTable>(table_owner);
        let sorted = *&table.players;  // copy

        // Bubble sort descending by ELO
        let len = vector::length(&sorted);
        let i   = 0u64;
        while (i < len) {
            let j = 0u64;
            while (j + 1 < len - i) {
                let a = vector::borrow(&sorted, j).elo;
                let b = vector::borrow(&sorted, j + 1).elo;
                if (a < b) {
                    vector::swap(&mut sorted, j, j + 1);
                };
                j = j + 1;
            };
            i = i + 1;
        };
        sorted
    }
}
