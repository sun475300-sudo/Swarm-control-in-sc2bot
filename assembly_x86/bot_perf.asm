; Phase 555: x86-64 Assembly
; SC2 Bot critical performance routines in NASM assembly

section .data
    ; String constants
    phase_msg    db "Phase 555: x86-64 Assembly - SC2 Bot Performance", 10, 0
    result_msg   db "Simulation result: minerals=%d workers=%d army=%d frame=%d", 10, 0
    fmt_int      db "%d", 10, 0

    ; Game constants
    MINERAL_THRESHOLD  dd 300
    WORKER_CAP         dd 22
    SUPPLY_BUFFER      dd 1
    OVERLORD_COST      dd 100
    DRONE_COST         dd 50
    ZERGLING_COST      dd 25
    OVERLORD_SUPPLY    dd 8

section .bss
    ; Game state (64-bit aligned)
    minerals     resq 1
    gas          resq 1
    supply       resq 1
    max_supply   resq 1
    workers      resq 1
    army         resq 1
    frame        resq 1
    hatcheries   resq 1

section .text
    global _start
    extern printf

; ─────────────────────────────────────────────
; init_state: Set initial game state
; ─────────────────────────────────────────────
init_state:
    push rbp
    mov rbp, rsp
    mov qword [minerals],   50
    mov qword [gas],        0
    mov qword [supply],     12
    mov qword [max_supply], 14
    mov qword [workers],    12
    mov qword [army],       0
    mov qword [frame],      0
    mov qword [hatcheries], 1
    pop rbp
    ret

; ─────────────────────────────────────────────
; tick_economy: Update minerals, increment frame
; workers * 8 / 10 → income
; ─────────────────────────────────────────────
tick_economy:
    push rbp
    mov rbp, rsp

    ; income = workers * 8 / 10
    mov rax, [workers]
    imul rax, 8
    mov rcx, 10
    xor rdx, rdx
    idiv rcx               ; rax = income

    add [minerals], rax    ; minerals += income
    inc qword [frame]      ; frame++

    pop rbp
    ret

; ─────────────────────────────────────────────
; decide_action:
; Returns action code in rax:
;   0 = wait
;   1 = train drone
;   2 = train zergling
;   3 = train overlord
;   4 = expand
; ─────────────────────────────────────────────
decide_action:
    push rbp
    mov rbp, rsp

    ; Check supply: if supply >= max_supply - 1 → overlord
    mov rax, [max_supply]
    sub rax, [rel SUPPLY_BUFFER wrt ..gotpc]  ; SUPPLY_BUFFER = 1
    cmp [supply], rax
    jl .check_worker
    mov rax, [minerals]
    cmp rax, 100
    jl .check_worker
    mov rax, 3         ; overlord
    jmp .done

.check_worker:
    ; if workers < WORKER_CAP && minerals >= 50
    mov rax, [workers]
    cmp rax, 22
    jge .check_expand
    mov rax, [minerals]
    cmp rax, 50
    jl .check_expand
    mov rax, 1         ; drone
    jmp .done

.check_expand:
    ; if minerals >= 300 && hatcheries < 3
    mov rax, [minerals]
    cmp rax, 300
    jl .check_army
    mov rax, [hatcheries]
    cmp rax, 3
    jge .check_army
    mov rax, 4         ; expand
    jmp .done

.check_army:
    ; if minerals >= 25 → zergling
    mov rax, [minerals]
    cmp rax, 25
    jl .wait
    mov rax, 2         ; zergling
    jmp .done

.wait:
    xor rax, rax       ; wait

.done:
    pop rbp
    ret

; ─────────────────────────────────────────────
; apply_action: execute action from rdi
; ─────────────────────────────────────────────
apply_action:
    push rbp
    mov rbp, rsp

    cmp rdi, 1         ; drone
    je .train_drone
    cmp rdi, 2         ; zergling
    je .train_zergling
    cmp rdi, 3         ; overlord
    je .train_overlord
    cmp rdi, 4         ; expand
    je .do_expand
    jmp .done

.train_drone:
    sub qword [minerals], 50
    inc qword [workers]
    inc qword [supply]
    jmp .done

.train_zergling:
    sub qword [minerals], 25
    add qword [army], 1
    inc qword [supply]
    jmp .done

.train_overlord:
    sub qword [minerals], 100
    add qword [max_supply], 8
    jmp .done

.do_expand:
    sub qword [minerals], 300
    inc qword [hatcheries]
    add qword [workers], 4
    jmp .done

.done:
    pop rbp
    ret

; ─────────────────────────────────────────────
; simulate_loop: run N frames (N in rdi)
; ─────────────────────────────────────────────
simulate_loop:
    push rbp
    mov rbp, rsp
    push rbx
    push r12

    mov r12, rdi        ; loop counter = N

.loop:
    test r12, r12
    jle .exit

    call tick_economy

    call decide_action
    mov rdi, rax        ; action code → first arg
    call apply_action

    dec r12
    jmp .loop

.exit:
    pop r12
    pop rbx
    pop rbp
    ret

; ─────────────────────────────────────────────
; _start entry point
; ─────────────────────────────────────────────
_start:
    ; Initialize
    call init_state

    ; Simulate 2000 frames
    mov rdi, 2000
    call simulate_loop

    ; Print results via printf
    mov rdi, result_msg
    mov rsi, [minerals]
    mov rdx, [workers]
    mov rcx, [army]
    mov r8,  [frame]
    xor rax, rax
    call printf

    ; Exit syscall
    mov rax, 60         ; sys_exit
    xor rdi, rdi        ; exit code 0
    syscall
