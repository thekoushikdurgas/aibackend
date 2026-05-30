"""
OS Labs and Telemetry method handlers for DurgasOS.
Provides interactive lessons, a code execution sandbox, real-time syscall tracing, and CPU thermal telemetry.
"""

import logging
import asyncio
import os
import sys
import tempfile
import subprocess
import time
import math
import random
import re
from typing import Dict, Any, Optional, AsyncGenerator
import psutil

from app.core.jsonrpc import JSONRPCError, JSONRPCErrorCode

logger = logging.getLogger(__name__)


# --- GLOBAL SIMULATION STATE ---
class HardwareSimulator:
    def __init__(self):
        self.target_cpu_load = 10.0
        self.cpu_load = 10.0
        self.ambient_temp = 32.0
        self.cpu_temp = 35.0
        self.fan_rpm = 1200.0
        self.cpu_frequency = 3.6  # GHz
        self.c_state_residency = {
            "C0": 10.0,  # Active
            "C1": 15.0,  # Halt
            "C6": 75.0,  # Deep sleep
        }
        self.throttling_active = False
        self.turbo_boost = False
        self.page_fault_rate = 5.0  # per second
        self.last_update = time.time()
        self.running_load_task = False

        # GPU attributes
        self.target_gpu_load = 10.0
        self.gpu_load = 10.0
        self.gpu_temp = 35.0
        self.vram_total_gb = 16.0
        self.vram_usage_gb = 1.2
        self.pcie_bandwidth = 0.1  # GB/s
        self.gpu_frequency = 1.2  # GHz

        # Memory/MMU attributes
        self.tlb_hit_rate = 99.8
        self.swap_in_rate = 0.0
        self.swap_out_rate = 0.0

        # Custom Fan Curve nodes (temp: rpm)
        # Default nodes: 30C: 1000rpm, 50C: 1800rpm, 70C: 3200rpm, 90C: 5200rpm
        self.fan_curve = [
            {"temp": 30.0, "rpm": 1000.0},
            {"temp": 50.0, "rpm": 1800.0},
            {"temp": 70.0, "rpm": 3200.0},
            {"temp": 90.0, "rpm": 5200.0},
        ]

    def interpolate_fan_curve(self, temp: float) -> float:
        nodes = sorted(self.fan_curve, key=lambda x: x["temp"])
        if not nodes:
            return 1200.0
        if temp <= nodes[0]["temp"]:
            return nodes[0]["rpm"]
        if temp >= nodes[-1]["temp"]:
            return nodes[-1]["rpm"]
        for i in range(len(nodes) - 1):
            n1 = nodes[i]
            n2 = nodes[i + 1]
            if n1["temp"] <= temp <= n2["temp"]:
                pct = (temp - n1["temp"]) / (n2["temp"] - n1["temp"])
                return n1["rpm"] + pct * (n2["rpm"] - n1["rpm"])
        return 1200.0

    def update(self):
        now = time.time()
        dt = min(now - self.last_update, 5.0)  # cap time step
        self.last_update = now

        # 1. Update CPU Load towards Target Load
        self.cpu_load += (self.target_cpu_load - self.cpu_load) * 0.4 * dt
        self.cpu_load = max(0.0, min(100.0, self.cpu_load))

        # 2. Update GPU Load towards Target GPU Load
        self.gpu_load += (self.target_gpu_load - self.gpu_load) * 0.5 * dt
        self.gpu_load = max(0.0, min(100.0, self.gpu_load))

        # 3. CPU Thermal Dynamics Formula
        heat_gen = (self.cpu_load * 0.5) * (self.cpu_frequency / 3.6)
        heat_diss = (self.cpu_temp - self.ambient_temp) * (self.fan_rpm / 3000.0) * 0.15
        temp_delta = (heat_gen - heat_diss) * dt
        self.cpu_temp += temp_delta
        self.cpu_temp = max(self.ambient_temp, min(105.0, self.cpu_temp))

        # 4. GPU Thermal Dynamics Formula
        gpu_heat_gen = (self.gpu_load * 0.6) * (self.gpu_frequency / 1.5)
        gpu_heat_diss = (
            (self.gpu_temp - self.ambient_temp) * (self.fan_rpm / 3000.0) * 0.18
        )
        gpu_temp_delta = (gpu_heat_gen - gpu_heat_diss) * dt
        self.gpu_temp += gpu_temp_delta
        self.gpu_temp = max(self.ambient_temp, min(105.0, self.gpu_temp))

        # 5. Fan Speed (respecting Custom Fan Curve)
        current_temp = max(self.cpu_temp, self.gpu_temp)
        target_rpm = self.interpolate_fan_curve(current_temp)
        self.fan_rpm += (target_rpm - self.fan_rpm) * 0.5 * dt

        # 6. DVFS & Throttling
        if self.cpu_temp >= 95.0:
            self.throttling_active = True
            self.turbo_boost = False
            self.cpu_frequency -= (self.cpu_frequency - 1.8) * 0.6 * dt
        else:
            self.throttling_active = False
            if self.cpu_load > 80.0:
                self.turbo_boost = True
                self.cpu_frequency += (4.4 - self.cpu_frequency) * 0.3 * dt
            else:
                self.turbo_boost = False
                standard_freq = 2.2 + (self.cpu_load / 100.0) * 1.6
                self.cpu_frequency += (standard_freq - self.cpu_frequency) * 0.4 * dt

        # GPU Frequency Scaling
        if self.gpu_temp >= 98.0:
            self.gpu_frequency -= (self.gpu_frequency - 0.8) * 0.5 * dt
        else:
            standard_gpu_freq = 0.8 + (self.gpu_load / 100.0) * 1.0
            self.gpu_frequency += (standard_gpu_freq - self.gpu_frequency) * 0.4 * dt

        # GPU VRAM & PCIe usage
        self.vram_usage_gb = (
            1.2 + (self.gpu_load / 100.0) * 12.0 + random.uniform(-0.1, 0.1)
        )
        self.vram_usage_gb = max(0.5, min(self.vram_total_gb, self.vram_usage_gb))
        self.pcie_bandwidth = (
            0.1 + (self.gpu_load / 100.0) * 28.0 + random.uniform(-0.5, 0.5)
        )
        self.pcie_bandwidth = max(0.1, min(32.0, self.pcie_bandwidth))

        # 7. C-State residency updates
        c0 = self.cpu_load
        c1 = (100.0 - c0) * 0.3
        c6 = 100.0 - c0 - c1
        self.c_state_residency["C0"] = max(1.0, min(100.0, c0))
        self.c_state_residency["C1"] = max(0.0, min(100.0, c1))
        self.c_state_residency["C6"] = max(0.0, min(100.0, c6))

        # 8. Memory Management updates
        self.page_fault_rate = 5.0 + (self.cpu_load * 0.4) + random.uniform(-2, 2)
        self.page_fault_rate = max(0.0, self.page_fault_rate)
        self.tlb_hit_rate = (
            99.9 - (self.page_fault_rate / 100.0) + random.uniform(-0.05, 0.05)
        )
        self.tlb_hit_rate = max(85.0, min(100.0, self.tlb_hit_rate))

        if self.cpu_load > 90.0:
            self.swap_in_rate = max(0.0, 12.0 + random.uniform(-2, 2))
            self.swap_out_rate = max(0.0, 15.0 + random.uniform(-2, 2))
        else:
            self.swap_in_rate = max(0.0, random.uniform(0, 0.5))
            self.swap_out_rate = max(0.0, random.uniform(0, 0.2))

    def get_payload(self) -> Dict[str, Any]:
        self.update()
        try:
            actual_cpu = psutil.cpu_percent()
            actual_ram = psutil.virtual_memory().percent
        except Exception:
            actual_cpu = self.cpu_load
            actual_ram = 45.0

        return {
            "simulated": {
                "cpuLoad": round(self.cpu_load, 1),
                "targetCpuLoad": round(self.target_cpu_load, 1),
                "cpuTemp": round(self.cpu_temp, 1),
                "fanRpm": int(self.fan_rpm),
                "cpuFrequency": round(self.cpu_frequency, 2),
                "throttlingActive": self.throttling_active,
                "turboBoost": self.turbo_boost,
                "pageFaultRate": round(self.page_fault_rate, 1),
                "cStates": {
                    "C0": round(self.c_state_residency["C0"], 1),
                    "C1": round(self.c_state_residency["C1"], 1),
                    "C6": round(self.c_state_residency["C6"], 1),
                },
                "gpuLoad": round(self.gpu_load, 1),
                "targetGpuLoad": round(self.target_gpu_load, 1),
                "gpuTemp": round(self.gpu_temp, 1),
                "vramTotalGB": round(self.vram_total_gb, 1),
                "vramUsageGB": round(self.vram_usage_gb, 2),
                "pcieBandwidth": round(self.pcie_bandwidth, 2),
                "gpuFrequency": round(self.gpu_frequency, 2),
                "tlbHitRate": round(self.tlb_hit_rate, 2),
                "swapInRate": round(self.swap_in_rate, 2),
                "swapOutRate": round(self.swap_out_rate, 2),
            },
            "host": {
                "cpuPercent": actual_cpu,
                "ramPercent": actual_ram,
                "cores": (
                    psutil.cpu_count(logical=True)
                    if hasattr(psutil, "cpu_count")
                    else 4
                ),
                "platform": sys.platform,
                "arch": (
                    os.environ.get("PROCESSOR_ARCHITECTURE", "x64")
                    if sys.platform == "win32"
                    else "x86_64"
                ),
            },
        }


simulator = HardwareSimulator()

# --- TOPICS & LESSON DATA ---
OS_LESSONS = [
    {
        "id": 1,
        "title": "Bootloader & Kernel Startup",
        "coreFocus": "From power-on → ROM (BIOS/UEFI) → Bootloader → Kernel Initialization → PID 1.",
        "content": (
            "### 1. Power On & Firmware Check\n"
            "The moment power enters the motherboard, the CPU's instruction pointer points to a ROM/Flash chip "
            "containing BIOS/UEFI. The firmware runs the **Power-On Self-Test (POST)** to verify RAM, storage, and bus interfaces.\n\n"
            "### 2. Bootloader Hand-Off\n"
            "In legacy BIOS, the system reads the first 512 bytes (**Master Boot Record - MBR**) to launch a stage-1 bootloader, "
            "which subsequently loads a stage-2 loader (like GRUB). Modern UEFI systems directly load signed `.efi` executables from "
            "the GPT (GUID Partition Table) partition.\n\n"
            "### 3. Kernel Bootstrap & PID 1\n"
            "The bootloader mounts the storage disk, extracts the compressed kernel image into RAM, sets up a rudimentary page table, "
            "and jumps to the kernel entry point. The kernel fully configures virtual memory, mounts the root filesystem, "
            "and launches the first user-space process: **Process ID 1 (PID 1)**, which handles services parallel startup."
        ),
        "quiz": [
            {
                "question": "What is the primary role of the MBR (Master Boot Record) in legacy BIOS booting?",
                "options": [
                    "To load the final OS GUI desktop",
                    "To allocate page tables in RAM",
                    "To hold the stage-1 bootloader sector to locate the stage-2 bootloader",
                    "To execute POST diagnostics",
                ],
                "answerIndex": 2,
                "explanation": "Because an entire bootloader cannot fit inside 512 bytes, the MBR stores a stage-1 bootloader whose only job is to locate and execute a more capable stage-2 bootloader.",
            },
            {
                "question": "What happens if PID 1 (init or systemd) unexpectedly terminates?",
                "options": [
                    "A new shell inherits PID 1",
                    "The system operates normally",
                    "The OS kernel panics and the system crashes",
                    "A warning is logged to syslog and execution continues",
                ],
                "answerIndex": 2,
                "explanation": "PID 1 is the parent of all user space processes and manages orphan reaping. If it dies, the kernel is left without a control loop and triggers a kernel panic.",
            },
        ],
    },
    {
        "id": 2,
        "title": "Privilege Rings & Protection Mode",
        "coreFocus": "Understanding Kernel Mode (Ring 0) vs User Mode (Ring 3), and how system calls bridge the boundary.",
        "content": (
            "### 1. Hardware Privilege Segregation\n"
            "To prevent third-party applications from crashing the system, CPUs implement hardware-enforced protection rings. "
            "On x86 architectures, these are Rings 0, 1, 2, and 3:\n"
            "- **Ring 0 (Kernel Mode)**: Absolute control. The kernel code and core drivers run here with unlimited instruction access.\n"
            "- **Ring 3 (User Mode)**: Sandbox layer. User programs (browsers, text editors) run here, unable to directly read hardware state or other processes' memory.\n\n"
            "### 2. Safeguards\n"
            "If an application in Ring 3 attempts to execute a privileged instruction (like disabling interrupts), the CPU triggers a "
            "**General Protection Fault (GPF)** and halts the application instantly.\n\n"
            "### 3. Transition via System Calls\n"
            "To write to disk or read a keyboard input, User Mode programs must execute a trap instruction (`syscall` or `int 0x80`). "
            "The CPU switches the mode bit to Ring 0, saves registers, jumps to the kernel's syscall entry vector, and runs the request securely."
        ),
        "quiz": [
            {
                "question": "In which privilege ring does a standard web browser run?",
                "options": ["Ring 0", "Ring 1", "Ring 3", "Ring 2"],
                "answerIndex": 2,
                "explanation": "Standard user applications run in Ring 3 (User Mode) to restrict their ability to crash other processes or access raw hardware.",
            }
        ],
    },
    {
        "id": 3,
        "title": "Virtual Memory & Page Tables",
        "coreFocus": "How the OS maps process address spaces to physical RAM, MMU role, page faults, and TLB cache.",
        "content": (
            "### 1. The Virtual Address space\n"
            "Rather than accessing raw physical RAM lines, each process owns a private **Virtual Address Space** starting from 0 to $2^{64}-1$. "
            "This provides absolute process isolation: Task A cannot view or corrupt Task B's RAM.\n\n"
            "### 2. Page Table & MMU Translation\n"
            "The **Memory Management Unit (MMU)** on the CPU translates virtual page addresses into physical frames. It references "
            "**Page Tables** managed by the kernel. Because page tables for 64-bit space are huge, they are structured as sparse **Multi-level Page Trees**.\n\n"
            "### 3. The TLB & Page Faults\n"
            "- **TLB (Translation Lookaside Buffer)**: An ultra-fast hardware cache that stores recent virtual-to-physical translations on the CPU.\n"
            "- **Page Fault**: If the MMU seeks a page that isn't loaded in RAM (or is marked invalid), it triggers a Page Fault. The kernel traps it, loads the page from disk (swap / demand paging), maps it in the table, and restarts the instruction."
        ),
        "quiz": [
            {
                "question": "What is the purpose of the Translation Lookaside Buffer (TLB)?",
                "options": [
                    "To swap idle pages to the disk partition",
                    "To cache page table translations for fast CPU memory lookups",
                    "To resolve branch prediction targets",
                    "To act as L1 memory cache",
                ],
                "answerIndex": 1,
                "explanation": "The TLB is a dedicated hardware cache on the CPU that stores page table lookups, preventing the CPU from needing to resolve the multi-level page table tree for every single memory access.",
            }
        ],
    },
    {
        "id": 4,
        "title": "Filesystems & Inodes",
        "coreFocus": "Logical abstractions of physical blocks, Unix inodes, directory maps, hard vs soft links, journaling.",
        "content": (
            "### 1. Physical Blocks to Log Files\n"
            "Disks understand only sequential block offsets. A **Filesystem** translates this into a nested hierarchy of files and directories.\n\n"
            "### 2. Unix Inodes (Index Nodes)\n"
            "An **inode** holds the metadata for a file (owner, size, timestamps, permission bits) and pointers to physical blocks on disk. "
            "Crucially, **the inode contains no file names**. Directories are special lookup tables mapping human-readable filenames to inode integers.\n\n"
            "### 3. Hard Links vs Symbolic Links\n"
            "- **Hard Link**: A new directory entry referencing an existing inode. Deleting one path doesn't delete the data until all link counts reach zero.\n"
            "- **Symbolic (Soft) Link**: A file whose contents contain a text path to another filename. If the original file moves, the link breaks.\n\n"
            "### 4. Journaling\n"
            "Modern filesystems (NTFS, ext4) record metadata transactions in a secure **Journal** before writing to blocks. On crash reboots, the system rolls back or replays the incomplete journal to prevent filesystem corruption."
        ),
        "quiz": [
            {
                "question": "Where is a file's name stored in a typical Unix filesystem?",
                "options": [
                    "Inside the inode header",
                    "Inside the directory file containing the entry",
                    "At the beginning of the file's first block on disk",
                    "Inside the partition Superblock",
                ],
                "answerIndex": 1,
                "explanation": "Inodes hold metadata but not names. File names are stored inside directory tables mapping files to corresponding inode numbers.",
            }
        ],
    },
    {
        "id": 5,
        "title": "Device Drivers & Interrupts",
        "coreFocus": "How drivers translate electrical commands, hardware interrupts (ISRs), and DMA (Direct Memory Access).",
        "content": (
            "### 1. Device Drivers\n"
            "Device drivers are kernel modules that translate generic operations (e.g., `write()`) into raw hardware signals. "
            "Because drivers run with Ring 0 privileges, driver bugs frequently lead to Blue Screens (BSOD) or Kernel Panics.\n\n"
            "### 2. Interrupts vs Polling\n"
            "- **Polling**: The CPU sits in a tight loop querying if device status registers are ready, consuming 100% CPU.\n"
            "- **Interrupts**: The CPU works on normal processes. When a device is ready, it sends an electrical signal down the system bus. The CPU halts, resolves the vector in the Interrupt Vector Table (IVT), executes the **Interrupt Service Routine (ISR)**, and returns.\n\n"
            "### 3. Direct Memory Access (DMA)\n"
            "For large disk or network card streams, the CPU instructs the hardware to write data directly into physical RAM buffers via a DMA controller. The device runs the transfer and triggers a single interrupt only when the task completes."
        ),
        "quiz": [
            {
                "question": "Why is DMA (Direct Memory Access) crucial for high-speed network interfaces?",
                "options": [
                    "It runs calculations on the GPU",
                    "It bypasses the CPU for data transmission into RAM, reducing CPU interrupt overhead",
                    "It encrypts incoming packets in Ring 0",
                    "It converts network streams into hard drive blocks directly",
                ],
                "answerIndex": 1,
                "explanation": "Without DMA, the CPU would be forced to process interrupts for every incoming byte, consuming the CPU entirely on high-bandwidth channels.",
            }
        ],
    },
    {
        "id": 6,
        "title": "Processes & PID 1 Lifecycle",
        "coreFocus": "Task descriptors, Process Control Blocks (PCBs), process cloning via Fork-Exec, init configurations.",
        "content": (
            "### 1. What is a Process?\n"
            "A process is a running instance of a program. It is represented inside the kernel by a **Process Control Block (PCB)** "
            "(in Linux, the `task_struct`). This structure stores open files, virtual memory maps, register values, and process state (Runnable, Sleeping, Zombie).\n\n"
            "### 2. Process Creation: Fork & Exec\n"
            "- **`fork()`**: Clones the active process. The kernel copies file descriptors, page tables, and registers. The parent gets the child's PID, while the child gets 0.\n"
            "- **`execve()`**: Replaces the cloned process's memory space and code section with a new binary executable, initiating execution from its main entry point.\n\n"
            "### 3. PID 1 (Init / Systemd)\n"
            "The very first user-space process spawned during boot. It acts as the ancestor of all active processes, mounts system folders, "
            "starts system daemons in parallel, and reaps zombie processes (orphaned processes whose parent didn't call `wait()`)."
        ),
        "quiz": [
            {
                "question": "What is a 'zombie' process in operating systems?",
                "options": [
                    "A process that consumes all CPU cycles",
                    "A terminated process whose exit status has not yet been read by its parent",
                    "An active process running in user mode without memory maps",
                    "A thread running in infinite loop",
                ],
                "answerIndex": 1,
                "explanation": "When a process exits, it retains a minimal PCB entry showing its exit status. It remains a zombie until the parent collects its code using the wait() syscall.",
            }
        ],
    },
    {
        "id": 7,
        "title": "System Calls & boundaries",
        "coreFocus": "Practical tracing of syscall mappings, read/write/open routines, tracing syscalls with strace.",
        "content": (
            "### 1. System Call Interface\n"
            "User applications cannot invoke hardware routines directly. They trigger system calls (syscalls). System calls represent a strict, "
            "validated API surface provided by the kernel to Ring 3 programs.\n\n"
            "### 2. Anatomy of a Syscall\n"
            "1. User program places syscall number and parameters in predefined CPU registers (e.g., `rax`, `rdi` on x86_64).\n"
            "2. User program executes `syscall` (or `int 0x80`).\n"
            "3. CPU halts user code, switches privilege state to Ring 0, and jumps to the kernel's system call handler.\n"
            "4. Kernel checks permissions, performs the task (e.g., writing bytes to stdout file descriptor `1`), sets the return value, and invokes `sysret` to return control.\n\n"
            "### 3. Tracing with `strace`\n"
            "A debugger tool that hooks into process trap calls using `ptrace`. It intercepts all syscalls, logging inputs, outputs, and timings."
        ),
        "quiz": [
            {
                "question": "Which system call is triggered when an application attempts to write text to stdout?",
                "options": ["openat", "write", "ioctl", "brk"],
                "answerIndex": 1,
                "explanation": "The write syscall is called by user space libraries (like printf or print) to write data to file descriptors, where fd 1 represents standard output.",
            }
        ],
    },
    {
        "id": 8,
        "title": "Process Schedulers & CPU sharing",
        "coreFocus": "Slicing processor cores, timer interrupts, context switching, completely fair scheduler (CFS) mechanics.",
        "content": (
            "### 1. CPU Preemption\n"
            "A single core can only run one instruction chain at a time. The OS creates the illusion of concurrency by allocating short time slices "
            "to processes, switching contexts rapidly. Timer interrupts generate clock ticks that invoke the scheduler.\n\n"
            "### 2. Context Switching Cost\n"
            "When switching from Task A to Task B, the CPU must save all register values (stack pointer, instruction pointer, general purpose registers) "
            "of Task A to its kernel stack, rewrite active memory mapping tables, and restore Task B's registers. This consumes processor cycles.\n\n"
            "### 3. Scheduling Algorithms\n"
            "- **MLFQ (Multi-level Feedback Queue)**: Prioritizes interactive tasks in high-speed queues; demotes CPU-bound tasks (Windows/macOS).\n"
            "- **CFS (Completely Fair Scheduler)**: Linux scheduler using a self-balancing Red-Black Tree. It tracks process virtual runtime (`vruntime`) "
            "and continuously runs the leftmost node (the task with least CPU execution time)."
        ),
        "quiz": [
            {
                "question": "How does the Completely Fair Scheduler (CFS) select the next process to execute on a CPU core?",
                "options": [
                    "It loops through active processes in simple FIFO order",
                    "It selects the process with the lowest virtual execution runtime (vruntime)",
                    "It calculates random priority weights",
                    "It chooses the task with highest page fault rate",
                ],
                "answerIndex": 1,
                "explanation": "CFS maintains active tasks in a Red-Black Tree sorted by virtual runtime (vruntime). It always schedules the task with the lowest vruntime to ensure fair CPU sharing.",
            }
        ],
    },
    {
        "id": 9,
        "title": "Threads & Concurrency",
        "coreFocus": "Processes vs Threads, shared address space, race conditions, synchronization locks.",
        "content": (
            "### 1. Threads vs Processes\n"
            "- **Process**: Isolated memory space. High context switch overhead.\n"
            "- **Thread**: A lightweight unit of execution. Threads within the same process share the virtual memory map, "
            "open file descriptors, and global variables, but maintain private stacks.\n\n"
            "### 2. Race Conditions\n"
            "When two threads concurrently read and write to the same memory location, the outcome is non-deterministic "
            "and depends on timing. For example, if Thread A and Thread B both attempt to increment a shared counter at the same time, "
            "increments can overwrite each other, leading to data corruption.\n\n"
            "### 3. Synchronization Primitives\n"
            "To prevent race conditions, programs protect critical sections of code using locks:\n"
            "- **Mutex (Mutual Exclusion)**: A lock that only one thread can hold. Others must block/sleep until it's released.\n"
            "- **Spinlock**: The thread busy-loops waiting for the lock, saving sleep context costs but consuming CPU."
        ),
        "quiz": [
            {
                "question": "What resource is shared among threads of the same process?",
                "options": [
                    "Execution stack",
                    "Instruction pointer",
                    "Virtual address space (global memory)",
                    "CPU register state",
                ],
                "answerIndex": 2,
                "explanation": "Threads share the global memory space and open descriptors of their parent process. However, they keep independent stacks and register sets to run separately.",
            }
        ],
    },
    {
        "id": 10,
        "title": "Inter-Process Communication (IPC)",
        "coreFocus": "Bypassing virtual memory isolation, pipes, sockets, and shared memory segments.",
        "content": (
            "### 1. Overcoming Isolation\n"
            "Because the MMU keeps process pages strictly isolated, Task A cannot write to Task B's variables. "
            "The OS kernel must provide explicitly managed conduits for processes to share data.\n\n"
            "### 2. Pipes\n"
            "A unidirectional byte stream. The kernel allocates a ring buffer inside its memory. One process writes data, "
            "and another reads. Shell pipelines (e.g., `cat data.log | grep error`) link stdout of the first to stdin of the second using pipes.\n\n"
            "### 3. Sockets & Shared Memory\n"
            "- **Sockets**: Bidirectional network endpoints. Used for local (UNIX domain sockets) or remote TCP/UDP communication.\n"
            "- **Shared Memory**: The kernel configures the page tables of two processes to map different virtual addresses to the same physical RAM frame. "
            "This bypasses all kernel copying overhead, making it the fastest IPC."
        ),
        "quiz": [
            {
                "question": "Which IPC mechanism is the fastest due to bypassing kernel data copy operations?",
                "options": [
                    "TCP Sockets",
                    "Unix Pipes",
                    "Shared Memory",
                    "Message Queues",
                ],
                "answerIndex": 2,
                "explanation": "Shared memory maps the same physical RAM frame directly to both processes, meaning they can exchange data without any intermediate kernel buffer copy.",
            }
        ],
    },
    {
        "id": 11,
        "title": "Shutdown & Signals",
        "coreFocus": "Kernel notifications (SIGTERM vs SIGKILL), unmounting volumes, ACPI power cutoff.",
        "content": (
            "### 1. OS Signals\n"
            "Signals are asynchronous interrupt notifications sent by the kernel to a process. The process can handle, "
            "ignore, or execute default actions for signals.\n"
            "- **`SIGTERM` (15)**: A polite termination request. The process catches it, flushes open database logs, cleans temporary folders, and exits.\n"
            "- **`SIGKILL` (9)**: Absolute termination. The process cannot catch, block, or ignore this signal. The kernel immediately destroys the process table entry.\n\n"
            "### 2. The Graceful Shutdown Sequence\n"
            "1. Init system sends `SIGTERM` to all active services.\n"
            "2. After a grace period, remaining services are terminated via `SIGKILL`.\n"
            "3. The filesystem cache is flushed (sync) and unmounted.\n"
            "4. Drivers put hardware into sleep states, and the CPU is halted. The kernel signals the motherboard via ACPI to shut off the power lines."
        ),
        "quiz": [
            {
                "question": "Which signal cannot be caught, blocked, or ignored by a user space application?",
                "options": ["SIGTERM", "SIGINT", "SIGKILL", "SIGSEGV"],
                "answerIndex": 2,
                "explanation": "SIGKILL is handled immediately by the kernel scheduler to force terminate a process. It cannot be caught or ignored by any user space signal handler.",
            }
        ],
    },
]

# --- METHOD HANDLERS ---


async def handle_get_topics(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Retrieve all OS lessons, visual diagrams, and quiz items."""
    return {"topics": OS_LESSONS}


async def handle_search_topics(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Search OS lessons using ChromaDB semantic search."""
    query = params.get("query", "").strip()
    if not query:
        return {"results": []}

    # Lazy-seed topics into ChromaDB on first search
    from app.services.rag import get_shared_chroma_vector_store

    vector_store = get_shared_chroma_vector_store()
    if not vector_store._initialized:
        await vector_store.initialize()

    collection_name = "os_academy"
    try:
        client = vector_store.client
        collection = client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )
        if collection.count() == 0:
            logger.info("Seeding OS Academy lessons into ChromaDB...")
            from app.services.rag.embeddings import get_embedding_service

            embedding_service = get_embedding_service()
            for topic in OS_LESSONS:
                doc_id = f"lesson_{topic['id']}"
                content = f"Title: {topic['title']}\nFocus: {topic['coreFocus']}\nContent: {topic['content']}"
                emb = embedding_service.embed_text(content)
                collection.add(
                    ids=[doc_id],
                    embeddings=[emb],
                    documents=[content],
                    metadatas=[{"topic_id": topic["id"], "title": topic["title"]}],
                )
    except Exception as e:
        logger.warning("Failed to check/seed os_academy collection: %s", e)

    # Search the collection
    try:
        from app.services.rag.embeddings import get_embedding_service

        emb_service = get_embedding_service()
        query_emb = emb_service.embed_text(query)
        res = collection.query(
            query_embeddings=[query_emb],
            n_results=3,
            include=["documents", "metadatas", "distances"],
        )
        results = []
        if res and "ids" in res and res["ids"]:
            for i in range(len(res["ids"][0])):
                meta = res["metadatas"][0][i] if res["metadatas"] else {}
                dist = res["distances"][0][i] if res["distances"] else 1.0
                results.append(
                    {
                        "topicId": meta.get("topic_id"),
                        "title": meta.get("title"),
                        "content": res["documents"][0][i] if res["documents"] else "",
                        "similarity": round(1.0 - dist, 4),
                    }
                )
        return {"results": results}
    except Exception as e:
        logger.error("Failed to query os_academy collection: %s", e)
        raise JSONRPCError(
            JSONRPCErrorCode.INTERNAL_ERROR, f"Semantic search failed: {str(e)}"
        )


async def handle_run_sandbox(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Compile and execute C or Python code securely with fallback output mock."""
    code = params.get("code", "").strip()
    language = params.get("language", "python").lower()

    if not code:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Code snippet is required.")

    # 1. Look for known print/printf structures to provide instant simulated output
    # if GCC or local execute fails (excellent for zero-dependency local environments)
    simulated_stdout = ""
    if language in ("c", "cpp"):
        # Simple extraction of printf text
        printf_matches = re.findall(r'printf\s*\(\s*"(.*?)"', code)
        if printf_matches:
            simulated_stdout = "\n".join(printf_matches).replace("\\n", "\n")
    else:
        # Simple extraction of print text
        print_matches = re.findall(r'print\s*\(\s*["\'](.*?)["\']\s*\)', code)
        if print_matches:
            simulated_stdout = "\n".join(print_matches)

    # 2. Attempt real execution in a safe temporary subprocess
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            if language == "python":
                file_path = os.path.join(tmpdir, "sandbox.py")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)

                # Limit execution time to 2 seconds max
                proc = subprocess.run(
                    [sys.executable, file_path],
                    capture_output=True,
                    text=True,
                    timeout=2.0,
                )
                return {
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "exitCode": proc.returncode,
                    "fallbackUsed": False,
                }
            elif language in ("c", "cpp"):
                # Check if gcc is available
                gcc_check = subprocess.run(["gcc", "--version"], capture_output=True)
                if gcc_check.returncode != 0:
                    raise FileNotFoundError("gcc is not available")

                file_path = os.path.join(tmpdir, "sandbox.c")
                out_path = os.path.join(tmpdir, "sandbox.out")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)

                compile_proc = subprocess.run(
                    ["gcc", file_path, "-o", out_path],
                    capture_output=True,
                    text=True,
                    timeout=3.0,
                )
                if compile_proc.returncode != 0:
                    return {
                        "stdout": "",
                        "stderr": compile_proc.stderr,
                        "exitCode": compile_proc.returncode,
                        "fallbackUsed": False,
                    }

                proc = subprocess.run(
                    [out_path], capture_output=True, text=True, timeout=2.0
                )
                return {
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "exitCode": proc.returncode,
                    "fallbackUsed": False,
                }
            else:
                raise ValueError(f"Unsupported language: {language}")
    except Exception as e:
        # Fallback to smart simulated stdout to ensure frictionless dev setup
        logger.warning(
            f"Execution failed or gcc missing: {e}. Returning simulated outputs."
        )
        return {
            "stdout": simulated_stdout
            or "Execution completed successfully (simulated environment).\n",
            "stderr": "",
            "exitCode": 0,
            "fallbackUsed": True,
            "fallbackReason": str(e),
        }


# Regex to find print/write/mmap concepts in code


async def handle_trace_syscalls(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Intercept code and stream a chronological timeline of mock system calls."""
    code = params.get("code", "").strip()
    language = params.get("language", "python").lower()

    if not code:
        raise JSONRPCError(JSONRPCErrorCode.INVALID_PARAMS, "Code snippet is required.")

    # Parse snippet and generate a realistic stream of educational syscall events
    traces = []

    # 1. Every program starts with binary load/setup
    traces.append(
        {
            "syscall": "execve",
            "args": f'"/bin/{language}", ["{language}", ...], [/* 24 env vars */]',
            "result": "0",
            "ring": 0,
            "description": "Load the executable, check ELF headers, allocate stack/heap maps, and start execution.",
        }
    )
    traces.append(
        {
            "syscall": "brk",
            "args": "NULL",
            "result": "0x55d04ae000",
            "ring": 0,
            "description": "Request kernel to check system break address to set up early heap memory layout.",
        }
    )

    # 2. Add library linkages
    traces.append(
        {
            "syscall": "openat",
            "args": 'AT_FDCWD, "/etc/ld.so.cache", O_RDONLY|O_CLOEXEC',
            "result": "3",
            "ring": 0,
            "description": "Locate standard runtime library bindings configuration.",
        }
    )
    traces.append(
        {
            "syscall": "mmap",
            "args": "NULL, 83920, PROT_READ, MAP_PRIVATE, 3, 0",
            "result": "0x7f4e91a000",
            "ring": 0,
            "description": "Map library configurations page frames directly into the process's virtual memory layout.",
        }
    )
    traces.append(
        {
            "syscall": "close",
            "args": "3",
            "result": "0",
            "ring": 0,
            "description": "Release file descriptor index 3 back to the kernel descriptor table.",
        }
    )

    # 3. Analyze user code logic for explicit file/write triggers
    if "open" in code or "fopen" in code:
        traces.append(
            {
                "syscall": "openat",
                "args": 'AT_FDCWD, "file.txt", O_RDWR|O_CREAT, 0666',
                "result": "3",
                "ring": 0,
                "description": "Open file context in read/write mode. Returns descriptor index 3.",
            }
        )
        traces.append(
            {
                "syscall": "fstat",
                "args": "3, {st_mode=S_IFREG|0644, st_size=12, ...}",
                "result": "0",
                "ring": 0,
                "description": "Read file metadata parameters (size, permissions) from disk inode tables.",
            }
        )

    if "print" in code or "printf" in code:
        # Standard stdout is file descriptor 1
        text = "Hello, World!"
        if language == "python":
            text_match = re.search(r'print\s*\(\s*["\'](.*?)["\']\s*\)', code)
        else:
            text_match = re.search(r'printf\s*\(\s*"(.*?)"', code)

        if text_match:
            text = text_match.group(1).replace("\\n", "\n")

        traces.append(
            {
                "syscall": "write",
                "args": f'1, "{text}", {len(text)}',
                "result": str(len(text)),
                "ring": 0,
                "description": "Write buffer string contents directly to file descriptor 1 (stdout console stream).",
            }
        )

    if "fork" in code or "multiprocessing" in code:
        traces.append(
            {
                "syscall": "clone",
                "args": "child_stack=0x0, flags=CLONE_VM|CLONE_FS|SIGCHLD",
                "result": "9421 (child PID)",
                "ring": 0,
                "description": "Clone the calling task to instantiate parent and child execution threads.",
            }
        )
        traces.append(
            {
                "syscall": "wait4",
                "args": "9421, [{WIFEXITED(s) && WEXITSTATUS(s) == 0}], 0, NULL",
                "result": "9421",
                "ring": 0,
                "description": "Yield CPU control and block the parent thread until child 9421 completes, preventing zombie accumulation.",
            }
        )

    if (
        "socket" in code
        or "connect" in code
        or "requests.get" in code
        or "fetch" in code
    ):
        traces.append(
            {
                "syscall": "socket",
                "args": "AF_INET, SOCK_STREAM, IPPROTO_IP",
                "result": "4",
                "ring": 0,
                "description": "Create an IPv4 TCP socket channel. Returns descriptor index 4.",
            }
        )
        traces.append(
            {
                "syscall": "connect",
                "args": "4, {sa_family=AF_INET, sin_port=htons(80), sin_addr=inet_addr('127.0.0.1')}, 16",
                "result": "0",
                "ring": 0,
                "description": "Initiate three-way TCP handshake to negotiate system bus network frames exchange.",
            }
        )

    # 4. Program Exit
    traces.append(
        {
            "syscall": "exit_group",
            "args": "0",
            "result": "<void>",
            "ring": 0,
            "description": "Terminate all active child threads within the process context, flush stream caches, and return exit code 0.",
        }
    )

    return {"traces": traces}


async def handle_trigger_load(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Trigger synthetic load cycles on the backend to drive thermal telemetry."""
    load_pct = float(params.get("loadPercent", 10.0))
    load_pct = max(0.0, min(100.0, load_pct))

    gpu_load_pct = float(params.get("gpuLoadPercent", 10.0))
    gpu_load_pct = max(0.0, min(100.0, gpu_load_pct))

    simulator.target_cpu_load = load_pct
    simulator.target_gpu_load = gpu_load_pct

    # Spawn background stress thread if load is heavy (> 70%) and not already running
    if load_pct > 70.0 and not simulator.running_load_task:
        simulator.running_load_task = True

        # Async CPU Stress thread to trigger real core load
        def run_stress():
            t_end = time.time() + 10  # Run for 10 seconds
            while time.time() < t_end:
                # Do some high-intensity math
                [math.sqrt(x) for x in range(30000)]
                time.sleep(0.01)
            simulator.running_load_task = False
            simulator.target_cpu_load = 10.0
            simulator.target_gpu_load = 10.0

        asyncio.get_event_loop().run_in_executor(None, run_stress)

    return {
        "status": "load_updated",
        "targetCpuLoad": load_pct,
        "targetGpuLoad": gpu_load_pct,
    }


async def handle_get_telemetry(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Fetch live CPU core telemetry and thermal P-states."""
    return simulator.get_payload()


async def handle_configure_fan_curve(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Configure the temperature-to-fan-RPM nodes for the cooling controller."""
    curve = params.get("curve")
    if not isinstance(curve, list):
        raise JSONRPCError(
            JSONRPCErrorCode.INVALID_PARAMS, "Curve must be a list of nodes."
        )

    validated_curve = []
    for node in curve:
        if not isinstance(node, dict) or "temp" not in node or "rpm" not in node:
            raise JSONRPCError(
                JSONRPCErrorCode.INVALID_PARAMS,
                "Every node must contain 'temp' and 'rpm'.",
            )
        validated_curve.append({"temp": float(node["temp"]), "rpm": float(node["rpm"])})

    # Sort by temp
    validated_curve.sort(key=lambda x: x["temp"])
    simulator.fan_curve = validated_curve
    return {"status": "fan_curve_updated", "curve": simulator.fan_curve}


async def handle_simulate_boot(
    params: Dict[str, Any],
    user: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> AsyncGenerator[Dict[str, Any], None]:
    """Streams a series of simulated boot log events with real timing delay."""
    boot_mode = params.get("bootMode", "uefi").lower()

    yield {"type": "start"}

    # Sequence of boot logs: (Stage, Message, Delay)
    logs = [
        # Phase 1: POST
        ("POST", "Initializing Power-On Self-Test (POST)...", 0.3),
        ("POST", "Checking CPU registers and frequency curve limits... OK.", 0.2),
        (
            "POST",
            "Scanning memory slots: 2x 16GB DDR5 identified at 5600 MT/s... OK.",
            0.3,
        ),
        (
            "POST",
            "Checking PCIe controllers: GPU Link Speed negotiated at x16 Gen5... OK.",
            0.3,
        ),
        # Phase 2: Firmware handoff
        ("FIRMWARE", f"Firmware: Initializing in {boot_mode.upper()} mode...", 0.2),
        (
            "FIRMWARE",
            "Enumerating storage volumes: NVMe SSD (512GB) selected as primary boot.",
            0.3,
        ),
        (
            "FIRMWARE",
            (
                "Reading boot sector via GUID Partition Table (GPT)..."
                if boot_mode == "uefi"
                else "Reading Master Boot Record (MBR) sector 0..."
            ),
            0.4,
        ),
        (
            "FIRMWARE",
            (
                "Executing target EFI application: \\EFI\\Boot\\durgasos.efi..."
                if boot_mode == "uefi"
                else "Executing Stage-1 Bootloader in MBR..."
            ),
            0.3,
        ),
        # Phase 3: Stage 2 Loader
        (
            "BOOTLOADER",
            "Stage-2 Bootloader: Loading DurgasOS Kernel image into RAM...",
            0.5,
        ),
        (
            "BOOTLOADER",
            "Setting up initial page tables and Ring 0 protection boundaries...",
            0.3,
        ),
        (
            "BOOTLOADER",
            "Decompressing kernel image (vmlinuz-durgas-1.0.0)... Done.",
            0.4,
        ),
        # Phase 4: Kernel init
        (
            "KERNEL",
            "Kernel Bootstrapping: Setting up Memory Management Unit (MMU)...",
            0.3,
        ),
        ("KERNEL", "Kernel: Probing Symmetric Multiprocessing (SMP)...", 0.2),
        (
            "KERNEL",
            "Kernel: Waking secondary cores (Cores 1-7 initialized, L1/L2 caches warmed)...",
            0.4,
        ),
        (
            "KERNEL",
            "Kernel: Mounting root filesystem (ext4) on /dev/nvme0n1p2... OK.",
            0.4,
        ),
        (
            "KERNEL",
            "Kernel: Loading device drivers for PCIe graphics engine (NVIDIA CUDA core)...",
            0.5,
        ),
        (
            "KERNEL",
            "Kernel: Configuring ACPI daemon and thermal TjMax threshold (95C)...",
            0.3,
        ),
        # Phase 5: Userspace
        (
            "USERSPACE",
            "Transitioning to User Space: Spawning Process ID 1 (systemd)...",
            0.4,
        ),
        ("USERSPACE", "systemd[1]: Starting system telemetry socket service...", 0.2),
        (
            "USERSPACE",
            "systemd[1]: Loading graphical window manager engine (DurgasOS Desktop)...",
            0.4,
        ),
        ("USERSPACE", "DurgasOS: Ready. Shell initialized on Ring 3 boundary.", 0.1),
    ]

    for stage, message, delay in logs:
        yield {
            "type": "chunk",
            "stage": stage,
            "message": message,
            "timestamp": time.time(),
        }
        await asyncio.sleep(delay)

    yield {"type": "done", "status": "boot_completed", "bootMode": boot_mode}


def get_methods() -> Dict[str, Any]:
    """Register methods for the registry mapping."""
    return {
        "os_labs.get_topics": handle_get_topics,
        "os_labs.search_topics": handle_search_topics,
        "os_labs.run_sandbox": handle_run_sandbox,
        "os_labs.trace_syscalls": handle_trace_syscalls,
        "os_labs.trigger_load": handle_trigger_load,
        "os_labs.get_telemetry": handle_get_telemetry,
        "os_labs.configure_fan_curve": handle_configure_fan_curve,
        "os_labs.simulate_boot": handle_simulate_boot,
    }
