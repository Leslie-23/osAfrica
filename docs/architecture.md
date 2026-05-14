# osAfrica Architecture

## System Layers

```
┌──────────────────────────────────────────────────────┐
│ Layer 5: AI Desktop                                  │
│   Wayland compositor (labwc fork) + AI panel overlay │
│   GTK4 panel + AI-integrated terminal                │
├──────────────────────────────────────────────────────┤
│ Layer 4: AI Shell                                    │
│   Natural language terminal (prompt_toolkit)         │
│   Intent parsing, command execution, history         │
├──────────────────────────────────────────────────────┤
│ Layer 3: AI Orchestration                            │
│   Router daemon (classifier + dispatcher)            │
│   System agents (resource, security, self-heal)      │
│   Code intelligence (assistant, reviewer, debugger)  │
├──────────────────────────────────────────────────────┤
│ Layer 2: AI Inference                                │
│   llama-swap proxy → llama-server instances          │
│   Llama 3 8B (general) + Qwen Coder (code)          │
│   Hardware-based model/quantization selection        │
├──────────────────────────────────────────────────────┤
│ Layer 1: Base Linux                                  │
│   Debian Trixie, systemd, Wayland, PipeWire          │
│   live-build ISO, Calamares installer                │
└──────────────────────────────────────────────────────┘
```

## Data Flow

```
User Input
    │
    ▼
osa-shell (Python REPL)
    │ classify intent
    ▼
osa-routerd (Unix socket /run/osa/router.sock)
    │ route to model
    ▼
llama-swap (:8080, OpenAI-compatible API)
    │
    ├──► llama-server :8081 (Llama 3 8B) ──► general response
    │
    └──► llama-server :8082 (Qwen Coder) ──► code response
    │
    ▼
osa-shell
    │ parse response, extract command
    ▼
osa-sandbox (bubblewrap)
    │ execute in sandboxed environment
    ▼
Output to user
```

## Memory Tiers

| RAM   | General Model        | Code Model           | Mode        |
|-------|---------------------|-----------------------|-------------|
| 8 GB  | Llama 3 Q4_K_S (4.5G)| None                 | Single      |
| 16 GB | Llama 3 Q4_K_M (5G) | Qwen 14B Q4_K_M (8.5G)| Swap      |
| 32 GB | Llama 3 Q4_K_M (5G) | Qwen 30B Q4_K_M (18G) | Concurrent |
| GPU   | + GPU offload        | + GPU offload         | Accelerated |

## IPC Map

| Component      | Endpoint                    | Protocol              |
|---------------|-----------------------------|-----------------------|
| llama-swap    | 127.0.0.1:8080              | HTTP (OpenAI compat)  |
| Llama 3       | 127.0.0.1:8081              | HTTP (OpenAI compat)  |
| Qwen Coder   | 127.0.0.1:8082              | HTTP (OpenAI compat)  |
| osa-routerd   | /run/osa/router.sock        | JSON-line over Unix   |
| osa-agentd    | /run/osa/agent.sock         | JSON-line over Unix   |
| Desktop ↔ AI  | Wayland protocol osa-ai-v1  | Wayland wire protocol |
