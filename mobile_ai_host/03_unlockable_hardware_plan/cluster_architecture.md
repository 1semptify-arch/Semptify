# Cluster Architecture — Multi-Phone AI Inference Cluster

This document describes how to wire multiple AI-host phones into a single
inference endpoint that you can query as if it were one big model server.

## Architecture Overview

```
                  ┌─────────────────┐
                  │   Load Balancer │  ← Single entry point
                  │   (Raspberry Pi │     for clients
                  │    or any PC)   │
                  └────────┬────────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────▼──────┐ ┌─────▼───────┐ ┌────▼───────┐
     │  Phone 1    │ │  Phone 2    │ │  Phone 3   │
     │  Pixel 4a   │ │  Pixel 4a   │ │  Pixel 4a  │
     │  Llama-3B   │ │  Llama-3B   │ │  Llama-3B  │
     │  :8080      │ │  :8080      │ │  :8080     │
     └─────────────┘ └─────────────┘ └────────────┘
```

## Three Cluster Modes

### Mode 1: Round-Robin (Simplest)

All phones run the **same model**. The load balancer sends each request to
the next phone in rotation. Best for **higher throughput** (more concurrent users).

- Pros: Simple, no coordination needed, any model works
- Cons: No single request is faster (same latency as one phone)
- Use case: Multiple users querying the same small model

### Mode 2: Model Sharding (Advanced)

Each phone runs a **different layer** of the same large model. Requests are
passed phone-to-phone through the layer stack. Best for **larger models**
that don't fit on one phone.

- Pros: Run 7B+ models across 2-4 phones
- Cons: Higher latency (sequential), complex setup, requires MPI or custom code
- Use case: Running Llama-3.2-7B across 2× Pixel 4a (3GB layers each)
- Tooling: `llama.cpp` supports `--rpc` for multi-node inference as of 2024

### Mode 3: Model Diversity (Recommended)

Each phone runs a **different model**. The load balancer routes based on
request type. Best for **different workloads**.

- Phone 1: Llama-3.2-3B (general chat)
- Phone 2: Qwen2-1.5B (fast coding)
- Phone 3: Phi-3.5-mini (long context)

- Pros: Right model for each task, parallel requests across models
- Cons: No single model gets faster
- Use case: A multi-purpose assistant that picks the right model per query

## Implementation: Mode 1 (Round-Robin with Nginx)

### On the Load Balancer (any PC or Raspberry Pi on the same network)

```nginx
# /etc/nginx/nginx.conf
events {}
http {
    upstream ai_nodes {
        least_conn;  # send to the phone with fewest active requests
        server 192.168.1.101:8080;  # Phone 1
        server 192.168.1.102:8080;  # Phone 2
        server 192.168.1.103:8080;  # Phone 3
    }

    server {
        listen 8080;

        # Streaming responses (llama.cpp uses SSE for /v1/chat/completions stream=true)
        proxy_buffering off;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;

        location / {
            proxy_pass http://ai_nodes;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_http_version 1.1;
            proxy_set_header Connection "";
        }

        # Health check endpoint
        location /health {
            proxy_pass http://ai_nodes/health;
        }
    }
}
```

```bash
sudo nginx -t && sudo systemctl reload nginx
```

Now clients point at the load balancer:
```bash
curl http://<load-balancer-ip>:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama-3.2-3b","messages":[{"role":"user","content":"Hello"}]}'
```

## Implementation: Mode 2 (Model Sharding with llama.cpp RPC)

llama.cpp supports multi-node inference via RPC as of 2024. Each phone runs
an `llama-rpc` server, and one "master" node coordinates.

### On each phone (worker):

```bash
# Phone 1 — runs layers 0-15
~/llama.cpp/build/bin/llama-rpc --host 0.0.0.0 --port 50052

# Phone 2 — runs layers 16-31
~/llama.cpp/build/bin/llama-rpc --host 0.0.0.0 --port 50052
```

### On the master node (can be a phone or a PC):

```bash
~/llama.cpp/build/bin/llama-server \
  -m ~/models/Llama-3.2-7B-Instruct-Q4_K_M.gguf \
  --host 0.0.0.0 --port 8080 \
  --rpc 192.168.1.101:50052,192.168.1.102:50052 \
  -t 8 -c 4096 -ngl 0
```

The master splits the model across the RPC workers. Clients talk only to the master.

**Note:** RPC mode is slower than single-node due to network latency between layers.
Use it only when the model won't fit on one phone.

## Implementation: Mode 3 (Model Diversity with HAProxy)

```haproxy
# /etc/haproxy/haproxy.cfg
global
    log stdout format raw local0

defaults
    log global
    mode http
    timeout client 600s
    timeout server 600s

frontend ai_gateway
    bind *:8080
    acl is_code path_beg /v1/code
    acl is_chat path_beg /v1/chat
    acl is_long  req.hdr(X-Model) -i phi-3.5

    use_backend code_model  if is_code
    use_backend long_model  if is_long
    default_backend chat_model

backend chat_model
    server phone1 192.168.1.101:8080

backend code_model
    server phone2 192.168.1.102:8080

backend long_model
    server phone3 192.168.1.103:8080
```

Clients route by path or header:
```bash
# General chat → Llama-3.2-3B on Phone 1
curl http://<gateway>:8080/v1/chat/completions ...

# Coding → Qwen2.5-Coder on Phone 2
curl http://<gateway>:8080/v1/code/completions ...

# Long context → Phi-3.5 on Phone 3
curl -H "X-Model: phi-3.5" http://<gateway>:8080/v1/chat/completions ...
```

## Network Setup

### Recommended: Wired Ethernet

For a permanent cluster, ditch Wi-Fi and use USB-Ethernet adapters on each phone.
Lower latency, no airtime contention.

```bash
# On each phone (postmarketOS):
sudo apk add usbutils
# Plug in USB-C → Ethernet adapter
sudo nmcli device connect eth0
```

### Static IPs

Assign static IPs in your router's DHCP reservation table, or on each phone:

```bash
# postmarketOS:
sudo nmcli connection modify wlan0 ipv4.addresses 192.168.1.101/24
sudo nmcli connection modify wlan0 ipv4.gateway 192.168.1.1
sudo nmcli connection modify wlan0 ipv4.method manual
sudo nmcli connection up wlan0
```

### VLAN Isolation (Optional)

For security, put the AI cluster on its own VLAN with no internet access
(models are pre-downloaded; the cluster doesn't need internet).

## Monitoring

### Per-Phone Health Check

```bash
# Simple check — run from the load balancer as a cron job:
for ip in 192.168.1.{101,102,103}; do
  if curl -sf --max-time 5 "http://$ip:8080/health" >/dev/null; then
    echo "$ip: OK"
  else
    echo "$ip: DOWN — rebooting"
    ssh ai@$ip "sudo reboot"
  fi
done
```

### Prometheus + Grafana (Advanced)

Install `node_exporter` on each phone:

```bash
sudo apk add node_exporter
sudo rc-update add node_exporter default
sudo rc-service node_exporter start
```

Then scrape from your Prometheus server:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'ai-phones'
    static_configs:
      - targets:
        - '192.168.1.101:9100'
        - '192.168.1.102:9100'
        - '192.168.1.103:9100'
```

Monitor: CPU temp, RAM used, requests/sec, tokens/sec per phone.

## Power Considerations

- Each phone draws ~3W idle, ~8W under AI load.
- 4 phones = ~32W peak. A single 50W USB-C charger can power all of them
  via a powered USB-C hub.
- **Remove batteries** for permanent installations (prevents swelling).
  The phone runs fine on USB power with battery disconnected.
- For battery-backed setups (acts as UPS during power outages), keep
  batteries installed but limit charge to 80% (see package 2 docs).

## Cost Calculation

| Component | Cost |
|-----------|------|
| 4× Pixel 4a used | $320 |
| 1× Powered USB-C hub (60W) | $30 |
| 1× Raspberry Pi 4 (load balancer) | $50 |
| 4× USB-C cables | $15 |
| 1× Small fan for cooling | $10 |
| **Total** | **~$425** |

For $425 you get a 4-node AI cluster with 24GB total RAM, capable of:
- 4× parallel Llama-3.2-3B inference (Mode 1)
- 1× sharded Llama-3.2-7B across 4 phones (Mode 2)
- 3× different models served simultaneously (Mode 3)

Comparable performance to a used GPU server costing $2000+.

## Next Steps

1. Get one phone working first (see `postmarketos_flash_guide.md`).
2. Add a second phone, set up Mode 1 round-robin with nginx.
3. Add phones 3 and 4, switch to Mode 3 (model diversity) for flexibility.
4. Add Prometheus monitoring once the cluster is stable.
