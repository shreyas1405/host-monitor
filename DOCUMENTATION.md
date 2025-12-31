# Host Monitor - Technical Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [System Design](#system-design)
3. [Implementation Details](#implementation-details)
4. [Module Breakdown](#module-breakdown)
5. [Algorithm Design](#algorithm-design)
6. [Data Flow](#data-flow)
7. [Error Handling](#error-handling)
8. [Performance Considerations](#performance-considerations)
9. [Security Considerations](#security-considerations)
10. [Testing Strategy](#testing-strategy)

---

## Architecture Overview

### High-Level Architecture

Host Monitor follows a **modular event-driven architecture** designed for continuous monitoring operations:

```
┌─────────────────────────────────────────────────┐
│         Configuration Management (YAML)          │
└──────────────────┬──────────────────────────────┘
                   │
┌──────────────────▼──────────────────────────────┐
│      Main Monitoring Loop (monitor.py)          │
├──────────────────────────────────────────────────┤
│  ├─ Host Availability Checker (ICMP Ping)      │
│  ├─ Service Port Scanner (TCP Connect)         │
│  ├─ State Management & Change Detection        │
│  └─ Alert Dispatcher                           │
└──────────────────┬──────────────────────────────┘
                   │
       ┌───────────┼───────────┐
       │           │           │
      ▼           ▼           ▼
   Console      CSV Logs    Alert Log
   Output      Storage     (Notifications)
```

### Key Components

1. **Configuration Loader**: Parses YAML config files
2. **Host Monitor Engine**: Core monitoring logic
3. **ICMP Ping Module**: Host availability checks
4. **TCP Port Scanner**: Service health checks
5. **State Tracker**: Maintains current status of all monitored entities
6. **Alert Manager**: Handles alert generation and delivery
7. **Logger System**: CSV-based logging for historical data

---

## System Design

### Design Patterns Used

#### 1. **Polling Pattern**
Continuous periodic checks instead of event-driven responses:
- Timer-based monitoring loop
- Configurable check interval (default: 30 seconds)
- Timeout protection prevents hanging operations

#### 2. **State Machine Pattern**
Each host/service has discrete states:
```
    ┌──────────┐
    │  ONLINE  │◄─────┐
    └────┬─────┘      │
         │ (3+ fails) │
         ▼            │
    ┌──────────┐      │
    │  OFFLINE │──────┘ (Success)
    └──────────┘
```

#### 3. **Observer Pattern**
Alert channels observe state changes:
- Console logger
- File logger
- Optional email notifier

#### 4. **Builder Pattern**
For constructing complex monitoring configurations from YAML.

### Concurrency Model

Current: **Sequential Polling** (Thread-safe by design)
- Single-threaded main loop
- Checks execute sequentially within each interval
- No race conditions

Future Enhancement: **Async/Threaded Model** (Optional upgrade path)
- Parallel monitoring of multiple hosts
- Improved responsiveness
- Better resource utilization

---

## Implementation Details

### Core Algorithms

#### Host Availability Check (ICMP Ping)
```python
1. Send ICMP echo request to target IP
2. Wait for response up to timeout duration
3. If response received → ONLINE
4. If timeout/no response → OFFLINE
5. Track consecutive failures
6. Generate alert if failures >= threshold
```

#### Service Port Check (TCP Connect)
```python
1. Create TCP socket
2. Attempt connection to target IP:port
3. If connected → ACCESSIBLE
4. If refused/timeout → UNREACHABLE
5. Close socket gracefully
6. Track state changes
```

#### State Change Detection
```python
for each monitoring entity (host/service):
    current_status = perform_check()
    previous_status = state_tracker[entity]
    
    if current_status != previous_status:
        increment_failure_counter()
    else:
        reset_failure_counter()
    
    if failure_counter >= threshold:
        trigger_alert()
        update_state()
```

### Configuration Processing

**YAML Parsing Flow:**
```
YAML Config → PyYAML Parser → Python Dict
                                    │
                                    ▼
                         Validation & Normalization
                                    │
                                    ▼
                          Object Construction
                                    │
                                    ▼
                          Monitoring Engine
```

### CSV Data Format

**CSV Schema:**
```csv
Columns: timestamp, event_type, host_name, ip_address, service_name, port, status, details

Example Row:
2025-01-01T10:30:20.123456,HOST_CHECK,web-server,192.168.1.100,,ONLINE,Ping successful (0.5ms)
2025-01-01T10:30:20.234567,SERVICE_CHECK,web-server,192.168.1.100,HTTP,80,ACCESSIBLE,Connection successful
2025-01-01T10:31:00.456789,ALERT,database-server,192.168.1.101,MySQL,3306,DOWN,Connection timeout after 5s
```

---

## Module Breakdown

### monitor.py - Main Module

**Key Functions:**

1. `load_config(filename)` → Dict
   - Loads and parses YAML configuration
   - Validates required fields
   - Returns config object

2. `check_host(host, timeout)` → bool
   - Sends ICMP ping
   - Returns True if reachable

3. `check_service(ip, port, timeout)` → bool
   - Attempts TCP connection
   - Returns True if accessible

4. `process_monitoring_result(result, previous_state)` → Alert
   - Compares current vs previous state
   - Determines if alert needed
   - Returns alert object or None

5. `log_event(timestamp, event_type, details, csv_writer)`
   - Writes structured log to CSV
   - Includes all relevant metadata

6. `send_alert(alert, channels)`
   - Dispatches alert to configured channels
   - Handles each channel independently

7. `main_monitoring_loop(config)`
   - Continuous monitoring execution
   - Handles timing and sequencing
   - Graceful shutdown on KeyboardInterrupt

---

## Data Flow

### Monitoring Cycle (Per Interval)

```
Start Monitoring Cycle
         │
         ▼
Read Configuration
         │
    ┌────┴─────┐
    │           │
    ▼           ▼
Check Hosts  Check Services
    │           │
    └─────┬─────┘
          ▼
    Process Results
          │
    ┌─────┴─────────┐
    │ Status Change? │
    └─────┬─────────┘
          │
       Yes│ No
    ┌─────▼──────┐
    │  Generate  │
    │   Alert    │
    └─────┬──────┘
          │
    ┌─────┴──────────┐
    │                │
    ▼                ▼
 Log Event      Update State
    │                │
    └────────┬───────┘
             ▼
   Send Alert (if triggered)
             │
             ▼
   Wait for Next Interval
             │
             ▼
   Repeat
```

---

## Error Handling

### Network Error Scenarios

| Scenario | Handling | Outcome |
|----------|----------|----------|
| Host unreachable | Increment failure counter | Mark as offline after threshold |
| Connection refused | Treat as service down | Immediate alert if persistent |
| Timeout | Retry on next cycle | Gradual failure accumulation |
| Invalid IP/hostname | Catch DNS errors | Log invalid config error |
| Permission denied (ping) | Fallback to TCP port check | Alternative verification method |

### Graceful Degradation

- **ICMP Unavailable**: Fall back to TCP port checking
- **File Write Error**: Log to console and continue
- **Invalid Config**: Use defaults for missing optional fields
- **Partial Failures**: Continue monitoring other targets

---

## Performance Considerations

### Timing Analysis

**Per-Cycle Time Breakdown** (e.g., 5 hosts, 2 services each, 5s timeout):
- Single host check: ~0.1-0.5ms (successful ping)
- Failed host check: ~5s (timeout)
- Service port check: ~0.1-1ms (successful)
- Failed service check: ~5s (timeout)
- CSV logging: ~1-2ms per event
- Total cycle with 10 entities: ~2-10 seconds (depends on failures)

### Optimization Opportunities

1. **Parallel Monitoring**: Use threading/async for concurrent checks
2. **Connection Pooling**: Reuse TCP connections for service checks
3. **Smart Timeouts**: Adaptive timeout based on historical response times
4. **Caching**: Cache DNS resolutions
5. **Batch CSV Writes**: Buffer events before writing

### Resource Usage

- **Memory**: ~50-100MB (varies with log size)
- **CPU**: <5% (I/O bound, minimal computation)
- **Network**: <1kbps (ping/TCP packets)
- **Disk**: ~1MB per 1000 log events

---

## Security Considerations

### Current Security Features

1. **YAML Config Validation**
   - Whitelist allowed IP addresses
   - Validate port ranges (1-65535)
   - Reject suspicious patterns

2. **File Permissions**
   - CSV logs created with 0o644 (readable)
   - Consider restricting to 0o640 for sensitive data

3. **Input Sanitization**
   - Hostname validation
   - Port range checking
   - Timeout bounds enforcement

### Recommended Security Enhancements

1. **Authentication**
   - API key for programmatic access
   - Multi-user support with RBAC

2. **Encryption**
   - TLS/SSL for email alerts
   - Encrypted log storage option
   - Credential encryption for stored passwords

3. **Audit Logging**
   - Track configuration changes
   - Log alert delivery attempts
   - Monitor failed access attempts

4. **Access Control**
   - Restrict configuration file permissions
   - Separate read/write permissions
   - Role-based alert filtering

---

## Testing Strategy

### Unit Testing Approach

**Test Categories:**

1. **Configuration Tests**
   - Valid YAML parsing
   - Invalid config handling
   - Missing field defaults

2. **Ping Module Tests**
   - Reachable host detection
   - Unreachable host detection
   - Timeout handling

3. **Port Scanner Tests**
   - Open port detection
   - Closed port detection
   - Connection timeout

4. **State Management Tests**
   - Status change detection
   - Counter increment/reset
   - Alert threshold logic

5. **CSV Logging Tests**
   - Data format validation
   - File creation
   - Append vs overwrite behavior

### Integration Testing

**End-to-End Scenarios:**
- Complete monitoring cycle
- Alert generation workflow
- Multi-host scenarios
- Mixed success/failure outcomes

### Performance Testing

- Cycle time measurement
- Memory usage tracking
- Large config file handling (100+ hosts)
- Long-running stability (24-48 hours)

### Manual Testing Checklist

- [ ] Start/stop monitoring cleanly
- [ ] Alert generation on service down
- [ ] Alert deduplication working
- [ ] CSV files created with correct format
- [ ] Configuration reloading (if implemented)
- [ ] Timeout protection effective
- [ ] Docker deployment working
- [ ] Multi-service monitoring per host

---

## API Reference (For Future Development)

### Programmatic Interface

```python
from host_monitor import HostMonitor

# Initialize
monitor = HostMonitor(config_file='targets.yaml')

# Register custom alert handler
monitor.register_alert_handler(callback_function)

# Start monitoring
monitor.start()

# Get current status
status = monitor.get_host_status('web-server')
# Returns: {'name': 'web-server', 'ip': '192.168.1.100', 'status': 'ONLINE'}

# Stop monitoring
monitor.stop()
```

---

## Future Architecture Enhancements

### Microservices Architecture
- **API Service**: REST interface for monitoring
- **Data Service**: Historical data storage
- **Alert Service**: Centralized alert management
- **Dashboard Service**: Web UI for visualization

### Event-Driven Redesign
- Message queue (RabbitMQ/Kafka)
- Event producers/consumers
- Webhook support
- Real-time updates via WebSocket

---

*Documentation Last Updated: January 2025*
*Applicable to: v1.0+*
