! Phase 554: Fortran HPC
! SC2 Bot matrix computations for combat simulation (array operations)

module sc2_types
    implicit none
    integer, parameter :: dp = selected_real_kind(15, 307)

    type :: Resources
        integer :: minerals  = 50
        integer :: gas       = 0
        integer :: supply    = 12
        integer :: max_supply = 14
    end type

    type :: ArmyStats
        integer    :: my_supply    = 0
        integer    :: enemy_supply = 0
        real(dp)   :: threat       = 0.0_dp
    end type

    type :: GameState
        type(Resources) :: res
        type(ArmyStats) :: army
        integer :: workers    = 12
        integer :: frame      = 0
        integer :: hatcheries = 1
    end type
end module

module sc2_combat
    use sc2_types
    implicit none

    ! Unit stats arrays: [zergling, roach, hydralisk, mutalisk, ultralisk]
    integer, parameter :: N_UNITS = 5
    real(dp) :: UNIT_DPS(N_UNITS)  = [8.9_dp, 10.0_dp, 15.6_dp, 9.0_dp, 59.6_dp]
    integer  :: UNIT_HP(N_UNITS)   = [35, 145, 90, 120, 500]
    integer  :: UNIT_RANGE(N_UNITS) = [0, 4, 5, 3, 1]  ! 0 = melee
    real(dp) :: UNIT_SPEED(N_UNITS) = [4.69_dp, 2.25_dp, 2.25_dp, 4.13_dp, 2.9_dp]

contains

    ! Compute DPS matrix: result(i,j) = effective DPS of unit i vs unit j
    subroutine compute_dps_matrix(dps_matrix)
        real(dp), intent(out) :: dps_matrix(N_UNITS, N_UNITS)
        integer :: i, j
        real(dp) :: range_bonus

        do i = 1, N_UNITS
            do j = 1, N_UNITS
                range_bonus = 1.0_dp
                ! Range advantage gives 10% bonus
                if (UNIT_RANGE(i) > UNIT_RANGE(j)) range_bonus = 1.1_dp
                dps_matrix(i, j) = UNIT_DPS(i) * range_bonus
            end do
        end do
    end subroutine

    ! Simulate battle outcome using DPS matrix
    function battle_result(my_counts, enemy_counts) result(winner)
        integer, intent(in) :: my_counts(N_UNITS), enemy_counts(N_UNITS)
        real(dp) :: dps_matrix(N_UNITS, N_UNITS)
        real(dp) :: my_effective_dps, enemy_effective_dps
        character(len=10) :: winner

        call compute_dps_matrix(dps_matrix)

        ! My total DPS against enemy
        my_effective_dps = 0.0_dp
        enemy_effective_dps = 0.0_dp

        ! Vectorized DPS computation
        my_effective_dps = sum(real(my_counts, dp) * UNIT_DPS)
        enemy_effective_dps = sum(real(enemy_counts, dp) * UNIT_DPS)

        if (my_effective_dps > enemy_effective_dps * 1.2_dp) then
            winner = "WIN"
        else if (enemy_effective_dps > my_effective_dps * 1.2_dp) then
            winner = "LOSS"
        else
            winner = "DRAW"
        end if
    end function

    ! Compute army value vector
    function army_value_vector(counts) result(value_vec)
        integer, intent(in) :: counts(N_UNITS)
        real(dp) :: value_vec(N_UNITS)
        integer :: i

        do i = 1, N_UNITS
            value_vec(i) = real(counts(i), dp) * UNIT_DPS(i) * &
                           real(UNIT_HP(i), dp) / 100.0_dp
        end do
    end function

end module

module sc2_economy
    use sc2_types
    implicit none

contains

    subroutine tick(state)
        type(GameState), intent(inout) :: state
        integer :: income
        income = state%workers * 8 / 10
        state%res%minerals = state%res%minerals + income
        state%frame = state%frame + 1
        state%army%threat = min(1.0_dp, state%army%threat + 0.0001_dp)
    end subroutine

    subroutine decide_and_apply(state)
        type(GameState), intent(inout) :: state
        integer :: supply_ratio_pct

        supply_ratio_pct = state%res%supply * 100 / max(1, state%res%max_supply)

        if (supply_ratio_pct >= 95 .and. state%res%minerals >= 100) then
            ! Build overlord
            state%res%minerals = state%res%minerals - 100
            state%res%max_supply = state%res%max_supply + 8
        else if (state%workers < 22 .and. state%res%minerals >= 50) then
            ! Train drone
            state%res%minerals = state%res%minerals - 50
            state%workers = state%workers + 1
            state%res%supply = state%res%supply + 1
        else if (state%res%minerals >= 300 .and. state%hatcheries < 3) then
            ! Expand
            state%res%minerals = state%res%minerals - 300
            state%hatcheries = state%hatcheries + 1
            state%workers = state%workers + 4
        else if (state%res%minerals >= 75 .and. state%res%gas >= 25) then
            ! Train roach
            state%res%minerals = state%res%minerals - 75
            state%res%gas = state%res%gas - 25
            state%army%my_supply = state%army%my_supply + 2
            state%res%supply = state%res%supply + 2
        else if (state%res%minerals >= 25) then
            ! Train zergling
            state%res%minerals = state%res%minerals - 25
            state%army%my_supply = state%army%my_supply + 1
            state%res%supply = state%res%supply + 1
        end if
    end subroutine

    subroutine simulate(state, n_frames)
        type(GameState), intent(inout) :: state
        integer, intent(in) :: n_frames
        integer :: i

        do i = 1, n_frames
            call tick(state)
            call decide_and_apply(state)
        end do
    end subroutine

end module

program main
    use sc2_types
    use sc2_combat
    use sc2_economy
    implicit none

    type(GameState) :: gs
    real(dp) :: dps_matrix(N_UNITS, N_UNITS)
    integer :: my_army(N_UNITS), enemy_army(N_UNITS)
    real(dp) :: value_vec(N_UNITS)
    character(len=10) :: outcome
    integer :: i, j

    write(*,*) "Phase 554: Fortran HPC — SC2 Combat Matrix"

    ! Economy simulation
    call simulate(gs, 2000)

    write(*,'(A,I6,A,I5,A,I3,A,I3,A,I3,A,I3)') &
        "Frame:", gs%frame, &
        " | Min:", gs%res%minerals, &
        " | W:", gs%workers, &
        " | A:", gs%army%my_supply, &
        " | S:", gs%res%supply, &
        "/", gs%res%max_supply

    ! Combat matrix
    call compute_dps_matrix(dps_matrix)
    write(*,*) ""
    write(*,*) "DPS Matrix (N_UNITS x N_UNITS):"
    do i = 1, N_UNITS
        write(*,'(5F8.2)') (dps_matrix(i,j), j=1,N_UNITS)
    end do

    ! Battle simulation
    my_army    = [5, 3, 4, 0, 0]  ! 5 zerglings, 3 roaches, 4 hydralisks
    enemy_army = [0, 5, 5, 0, 0]  ! 5 roaches, 5 hydralisks

    outcome = battle_result(my_army, enemy_army)
    value_vec = army_value_vector(my_army)

    write(*,*) ""
    write(*,'(A,A)') "Battle outcome: ", outcome
    write(*,'(A,5F8.2)') "Army value: ", value_vec
    write(*,'(A,F8.2)') "Total value: ", sum(value_vec)

end program
