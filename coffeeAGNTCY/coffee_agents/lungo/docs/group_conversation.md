<<<<<<< HEAD
# Group Conversation Agents Architecture

## Components
- Shipper (`logistic-shipper`): ...
- Accountant (`logistic-accountant`): ...
- Farm (`logistic-farm`): ...
- Supervisor (`logistic-supervisor`): Orchestrates and routes.
- SLIM Gateway (`logistic-slim`): PubSub (56400) + controller (56401).

## Ports
| Purpose | Port | Source |
|---------|------|--------|
| SLIM PubSub | 56400 | `logistic-server-config.yaml` |
| SLIM Controller | 56401 | `logistic-server-config.yaml` |

## Message Flow
1. Supervisor publishes request via SLIM PubSub.
2. Farms consume; unicast vs broadcast determined by routing logic.
3. Responses returned via subscribed channels.
4. Observability exported via OTLP to ClickHouse/Grafana.

## Environment Variables
- `DEFAULT_MESSAGE_TRANSPORT=SLIM`
- `TRANSPORT_SERVER_ENDPOINT=http://logistic-slim:56400`

## Extending
Add a new logistic service:
1. Define container in `docker-compose.logistic.yaml`.
2. Point `TRANSPORT_SERVER_ENDPOINT` to PubSub port.
3. Register any new routing logic in supervisor graph.
=======
# Group Conversation

This document explains how to run the logistics multi-agent conversation locally (via Docker Compose or individual `make` targets) and how an order progresses through the system.

---

## 1. Services / Agents

| Role                | Python entrypoint                              | Purpose                                                             |
|---------------------|-----------------------------------------------|---------------------------------------------------------------------|
| Logistic Supervisor | `agents/supervisors/logistic/main.py`         | Starts the workflow, handles user input, emits `RECEIVED_ORDER`     |
| Shipper Agent       | `agents/logistics/shipper/server.py`          | Progresses shipping states (`CUSTOMS_CLEARANCE`, `DELIVERED`)        |
| Accountant Agent    | `agents/logistics/accountant/server.py`       | Confirms payment (`PAYMENT_COMPLETE`)                                |
| Tatooine Farm Agent | `agents/logistics/farm/server.py`             | Moves order to `HANDOVER_TO_SHIPPER` after `RECEIVED_ORDER`          |

---

## 2. Order Lifecycle

Sequence (agent → state produced):

1. Supervisor → `RECEIVED_ORDER`  
2. Farm Agent → `HANDOVER_TO_SHIPPER`  
3. Shipper Agent → `CUSTOMS_CLEARANCE`  
4. Accountant Agent → `PAYMENT_COMPLETE`  
5. Shipper Agent → `DELIVERED` (final)  

### Transition Table

| From State        | To State              | Responsible Agent |
|-------------------|-----------------------|-------------------|
| (User Prompt)     | `RECEIVED_ORDER`      | Supervisor        |
| `RECEIVED_ORDER`  | `HANDOVER_TO_SHIPPER` | Farm Agent        |
| `HANDOVER_TO_SHIPPER` | `CUSTOMS_CLEARANCE` | Shipper Agent     |
| `CUSTOMS_CLEARANCE` | `PAYMENT_COMPLETE`   | Accountant Agent  |
| `PAYMENT_COMPLETE` | `DELIVERED`          | Shipper Agent     |

### Flow (ASCII)

```
User Prompt
↓
[Supervisor] → RECEIVED_ORDER → [Farm]
[Farm] → HANDOVER_TO_SHIPPER → [Shipper]
[Shipper] → CUSTOMS_CLEARANCE → [Accountant]
[Accountant] → PAYMENT_COMPLETE → [Shipper]
[Shipper] → DELIVERED (final)
```

---

## Run With Docker Compose (includes SLIM transport)

```sh
docker compose -f docker-compose.logistic.yaml up
```

Starts: supervisor, shipper, accountant, farm, SLIM transport.

---

## Run Individually (one terminal per service)
Terminal 1:
```sh
# The LLM env vars (e.g. `OPENAI_API_KEY`) are required the logistic-supervisor.
make logistic-supervisor
```
Terminal 2:
```sh
make shipper
```
Terminal 3:
```sh
make accountant
```
Terminal 4:
```sh
make logistic-farm
```
>>>>>>> main
