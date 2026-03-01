# Use-Case Diagram — Agentic Honeypot

Shows all system actors and their interactions with the honeypot API.

```mermaid
usecaseDiagram
    actor Scammer
    actor "Evaluation Platform\n(GUVI)" as Eval
    actor Admin
    actor "Demo User" as Demo

    rectangle "Agentic Honeypot System" {
        usecase UC1 as "Send Scam Message\n(POST /webhook)"
        usecase UC2 as "Detect Scam Intent"
        usecase UC3 as "Engage with Persona"
        usecase UC4 as "Extract Intelligence"
        usecase UC5 as "Send Final Intel Callback"
        usecase UC6 as "View GUI Dashboard\n(GET /gui)"
        usecase UC7 as "Run Showcase / Auto Mode\n(/api/chat/auto)"
        usecase UC8 as "Health Check\n(/health, /health/diag)"
        usecase UC9 as "Manage Config\n(/admin/config)"
        usecase UC10 as "View Timing Stats\n(/admin/timing)"
        usecase UC11 as "Stream Telemetry\n(/api/telemetry SSE)"
        usecase UC12 as "View War Room\n(/war-room)"
    }

    Scammer --> UC1
    UC1 ..> UC2 : <<include>>
    UC2 ..> UC3 : <<include>>
    UC3 ..> UC4 : <<include>>
    UC4 ..> UC5 : <<include>>

    Eval --> UC1 : Injects test scenarios
    UC5 --> Eval : POST final intel report

    Demo --> UC6
    Demo --> UC7
    Demo --> UC8

    Admin --> UC9
    Admin --> UC10
    Admin --> UC11
    Admin --> UC12
```
