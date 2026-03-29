! P99: FORTRAN - Scientific Computing for Battle Simulation
! High-performance numerical computation for combat analysis

module sc2_simulation
    implicit none
    
    type :: unit_data
        integer :: id
        real :: health
        real :: damage
        real :: position_x
        real :: position_y
        real :: velocity_x
        real :: velocity_y
    end type unit_data
    
    type :: battle_state
        type(unit_data), allocatable :: units(:)
        integer :: num_units
        real :: total_power
        real :: threat_level
    end type battle_state

contains

    subroutine initialize_battle(state, num_units)
        type(battle_state), intent(inout) :: state
        integer, intent(in) :: num_units
        integer :: i
        
        state%num_units = num_units
        allocate(state%units(num_units))
        
        do i = 1, num_units
            state%units(i)%id = i
            state%units(i)%health = 100.0
            state%units(i)%damage = 10.0
            state%units(i)%position_x = real(i) * 10.0
            state%units(i)%position_y = real(i) * 5.0
            state%units(i)%velocity_x = 0.0
            state%units(i)%velocity_y = 0.0
        end do
        
        call calculate_total_power(state)
    end subroutine initialize_battle

    subroutine calculate_total_power(state)
        type(battle_state), intent(inout) :: state
        integer :: i
        
        state%total_power = 0.0
        do i = 1, state%num_units
            state%total_power = state%total_power + &
                state%units(i)%health * state%units(i)%damage / 100.0
        end do
    end subroutine calculate_total_power

    subroutine simulate_battle_step(state, dt)
        type(battle_state), intent(inout) :: state
        real, intent(in) :: dt
        integer :: i
        
        do i = 1, state%num_units
            state%units(i)%position_x = state%units(i)%position_x + &
                state%units(i)%velocity_x * dt
            state%units(i)%position_y = state%units(i)%position_y + &
                state%units(i)%velocity_y * dt
        end do
        
        call calculate_threat_level(state)
    end subroutine simulate_battle_step

    subroutine calculate_threat_level(state)
        type(battle_state), intent(inout) :: state
        real :: avg_distance
        integer :: i, j
        real :: distance
        
        avg_distance = 0.0
        do i = 1, state%num_units
            do j = i+1, state%num_units
                distance = sqrt((state%units(i)%position_x - state%units(j)%position_x)**2 + &
                              (state%units(i)%position_y - state%units(j)%position_y)**2)
                avg_distance = avg_distance + distance
            end do
        end do
        
        if (state%num_units > 1) then
            avg_distance = avg_distance / (state%num_units * (state%num_units - 1) / 2)
        end if
        
        state%threat_level = 100.0 / (avg_distance + 1.0)
    end subroutine calculate_threat_level

    subroutine get_combat_recommendation(state, recommendation)
        type(battle_state), intent(in) :: state
        character(len=20), intent(out) :: recommendation
        
        if (state%total_power > 500.0) then
            recommendation = 'ATTACK'
        else if (state%total_power > 200.0) then
            recommendation = 'DEFEND'
        else if (state%threat_level > 0.5) then
            recommendation = 'RETREAT'
        else
            recommendation = 'EXPAND'
        end if
    end subroutine get_combat_recommendation

end module sc2_simulation

program main
    use sc2_simulation
    type(battle_state) :: battle
    character(len=20) :: action
    integer :: time_step
    
    print *, 'SC2 Battle Simulation (FORTRAN)'
    call initialize_battle(battle, 50)
    
    do time_step = 1, 100
        call simulate_battle_step(battle, 0.1)
        if (mod(time_step, 10) == 0) then
            call get_combat_recommendation(battle, action)
            print *, 'Step:', time_step, 'Power:', battle%total_power, 'Action:', action
        end if
    end do
    
    deallocate(battle%units)
end program main
