# Host & Service Monitoring Tool

## Project Overview

**Host Monitor** is a comprehensive host and service monitoring tool built with Python and containerized using Docker. It continuously monitors the health and availability of hosts and services on your network, providing real-time alerts and comprehensive reporting capabilities.

This tool was developed as part of a networking engineering project to address the need for lightweight, efficient host monitoring with minimal configuration overhead.

---

## Features

✅ **Real-time Host Monitoring**
  - Continuous ICMP ping monitoring of configured hosts
  - Configurable monitoring intervals and timeout thresholds
  - Automatic detection of host availability changes

✅ **Service Health Monitoring**
  - TCP port/service availability checks
  - Multi-service monitoring per host
  - Service status tracking and logging

✅ **Alert System**
  - Immediate notifications when hosts/services go down
  - Alert delivery via multiple channels (console, file, optional email)
  - Alert deduplication to prevent notification spam
  - Customizable alert thresholds

✅ **Data Logging & Reports**
  - Comprehensive event logging in CSV format
  - Historical data storage for trend analysis
  - Support for custom log locations

✅ **Configuration Management**
  - YAML-based configuration file for easy customization
  - Separate config examples provided
  - Support for complex monitoring scenarios

✅ **Docker Support**
  - Full Docker containerization
  - Pre-configured Dockerfile for easy deployment
  - Environment variable configuration support

---

## Project Structure

```
host-monitor/
├── monitor.py              # Main monitoring engine
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── config_example.yaml    # Example configuration file
├── targets.yaml           # Default monitoring targets
├── csv/                   # CSV logs directory (auto-created)
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

---

## Installation & Setup

### Option 1: Local Python Installation

**Prerequisites:**
- Python 3.8+
- pip (Python package manager)
- Linux/macOS (for ping functionality)

**Steps:**

1. Clone the repository:
```bash
git clone https://github.com/shreyas1405/host-monitor.git
cd host-monitor
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure your monitoring targets:
```bash
cp config_example.yaml targets.yaml
# Edit targets.yaml to add your hosts and services
```

4. Run the monitor:
```bash
python monitor.py
```

### Option 2: Docker Deployment

**Prerequisites:**
- Docker installed

**Steps:**

1. Clone and navigate to repository:
```bash
git clone https://github.com/shreyas1405/host-monitor.git
cd host-monitor
```

2. Build the Docker image:
```bash
docker build -t host-monitor:latest .
```

3. Create/configure your targets.yaml file

4. Run the container:
```bash
docker run -d \
  --name host-monitor \
  -v $(pwd)/targets.yaml:/app/targets.yaml \
  -v $(pwd)/csv:/app/csv \
  host-monitor:latest
```

---

## Configuration Guide

### Configuration File Structure (YAML)

```yaml
monitor_config:
  interval: 30          # Monitoring interval in seconds
  timeout: 5            # Ping timeout in seconds
  failed_threshold: 3   # Consecutive failures before alert
  log_file: "csv/monitoring.csv"
  alert_channels:
    - console           # Print alerts to console
    - file              # Log alerts to file
    # - email           # Optional: email alerts (configure separately)

hosts:
  - name: "web-server"
    ip: "192.168.1.100"
    services:
      - name: "HTTP"
        port: 80
      - name: "HTTPS"
        port: 443
  
  - name: "database-server"
    ip: "192.168.1.101"
    services:
      - name: "MySQL"
        port: 3306
```

### Configuration Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|----------|
| `interval` | int | Monitoring check interval (seconds) | 30 |
| `timeout` | int | Ping/connection timeout (seconds) | 5 |
| `failed_threshold` | int | Consecutive failures before alert | 3 |
| `log_file` | str | Path to CSV log file | csv/monitoring.csv |
| `alert_channels` | list | Alert notification methods | [console, file] |

---

## Usage Examples

### Basic Monitoring

Start monitoring with default configuration:
```bash
python monitor.py
```

Output:
```
[2025-01-01 10:30:15] MONITORING STARTED
[2025-01-01 10:30:20] ✓ web-server (192.168.1.100) - ONLINE
[2025-01-01 10:30:20] ✓ database-server (192.168.1.101) - ONLINE
[2025-01-01 10:30:20] ✓ HTTP (web-server:80) - ACCESSIBLE
[2025-01-01 10:30:20] ✓ MySQL (database-server:3306) - ACCESSIBLE
```

### Monitor with Custom Config

Specify a custom configuration file:
```bash
python monitor.py --config custom_config.yaml
```

### Check Monitoring Logs

View CSV logs:
```bash
cat csv/monitoring.csv
```

---

## Output & Logging

### Console Output

Real-time monitoring status:
- ✓ (Green) = Host/Service is online/accessible
- ✗ (Red) = Host/Service is offline/unreachable
- ⚠ (Yellow) = Warning state

### CSV Log Format

```csv
timestamp,event_type,host_name,ip_address,service_name,port,status,details
2025-01-01 10:30:20,HOST_CHECK,web-server,192.168.1.100,,ONLINE,Ping successful
2025-01-01 10:30:20,SERVICE_CHECK,web-server,192.168.1.100,HTTP,80,ACCESSIBLE,Connection successful
2025-01-01 10:31:20,ALERT,database-server,192.168.1.101,MySQL,3306,DOWN,Connection timeout
```

### Alert Log File

Alerts are logged to `csv/alerts.log`:
```
[ALERT] 2025-01-01 10:31:20 - database-server (192.168.1.101) OFFLINE
[ALERT] 2025-01-01 10:35:20 - MySQL service (port 3306) UNREACHABLE
[RECOVERY] 2025-01-01 10:36:00 - database-server (192.168.1.101) BACK ONLINE
```

---

## Technologies Used

| Technology | Version | Purpose |
|------------|---------|----------|
| Python | 3.8+ | Core monitoring logic |
| YAML | - | Configuration management |
| CSV | - | Data logging and reporting |
| Docker | Latest | Containerization |
| Socket | Built-in | Service port checking |
| ICMP/Ping | OS-level | Host availability checks |

---

## Dependencies

See `requirements.txt` for complete list:
- `PyYAML` - Configuration file parsing
- `ping3` - ICMP ping functionality
- Additional standard library modules (socket, csv, logging, etc.)

---

## Troubleshooting

### Issue: "Permission denied" when running ping
**Solution:** ICMP ping may require root privileges on some systems.
```bash
sudo python monitor.py
```

### Issue: Docker container exits immediately
**Check logs:**
```bash
docker logs host-monitor
```
Ensure your `targets.yaml` file is correctly formatted and mounted.

### Issue: Service port not checking correctly
**Verify:**
- Target service is actually running
- Firewall is not blocking the port
- Port number is correct in configuration

### Issue: CSV file grows too large
**Solution:** Implement log rotation (coming in future updates) or manually archive logs:
```bash
mv csv/monitoring.csv csv/monitoring_$(date +%Y%m%d).csv
```

---

## Future Enhancements

🚀 Planned features for upcoming versions:
- Email alerting integration with SMTP
- Web dashboard for monitoring visualization
- Database backend (PostgreSQL/MongoDB) for scalable storage
- Prometheus metrics export for Grafana integration
- SNMPv3 monitoring support
- Advanced analytics and trend prediction
- Multi-user authentication and role-based access control
- REST API for programmatic access
- Custom alert scripts/webhooks

---

## Project Learning Outcomes

This project demonstrates:
- ✅ Network protocol understanding (ICMP, TCP/IP, DNS)
- ✅ Python socket programming and system calls
- ✅ YAML configuration management
- ✅ Event-driven architecture and logging
- ✅ CSV data handling and storage
- ✅ Docker containerization practices
- ✅ Real-world monitoring system design
- ✅ Error handling and resilience

---

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

---

## License

MIT License - Feel free to use this project for educational and commercial purposes.

---

## Author

**Shreyas** - CSE Student, SJBIT  
Build Date: January 2025  
GitHub: [@shreyas1405](https://github.com/shreyas1405)  

For more projects and updates, visit my [portfolio](https://github.com/shreyas1405).

---

## Contact & Support

For questions, issues, or suggestions:
- Open an issue on GitHub
- Email: shreyas1405@gmail.com
- LinkedIn: [Profile](https://linkedin.com/in/shreyas-)

---

*Last Updated: January 2025*
