# RabbitMQ Integration for QR-Based Threat Analysis

This guide rationalizes and merges the previous README and overview documents, converts all instructions to bash, and offers a unified overview for Raspberry Pi integration.

---

## Goal & Flow

- **Raspberry Pi scans a QR code** (using [QR_SCAN](https://github.dxc.com/ireid5/QR_SCAN))
- **QR data is sent to RabbitMQ**
- **RabbitMQ consumer receives the message** and triggers:
  1. **A call to the SolrSim Flask app** via HTTP:  
     `http://localhost:5000/?query=<QR_DATA>`
  2. **A Node.js script call**:  
     `node S500.js --add --db <OP_AREA>` (from `src/static/js` in IES repo)

---

## 1. RabbitMQ Consumer (Python → Bash)

The Python consumer can be replaced by the following bash logic using `rabbitmqadmin` and standard utilities.  
**Note:** For production, Python is more robust, but here is a bash conceptual translation.

### Bash Example: Consuming Messages

```bash
# Requires: rabbitmqadmin, curl, node
# Install dependencies:
sudo apt update
sudo apt install rabbitmq-server curl nodejs npm

# Start RabbitMQ server
sudo systemctl start rabbitmq-server

# Download rabbitmqadmin:
wget http://localhost:15672/cli/rabbitmqadmin
chmod +x rabbitmqadmin

# Poll messages from 'qrscan' queue
while true; do
  msg=$(./rabbitmqadmin get queue=qrscan requeue=false | grep -Po '(?<="payload": ")[^"]+')
  if [ -n "$msg" ]; then
    # 1. Call Flask app
    curl "http://localhost:5000/?query=$msg"
    # 2. Call Node.js script
    op_area="${msg%%,*}"
    node /path/to/S500.js --add --db "$op_area"
  fi
  sleep 1
done
```

---

## 2. QR Code Scanner Producer (Python → Bash)

Assuming you have a way to scan QR codes and output a string (e.g., via a Python script, or using `zbarcam` for bash):

```bash
# Requires: zbar-tools
sudo apt install zbar-tools

# Scan QR and send to RabbitMQ
while true; do
  qr_data=$(zbarcam --raw)
  if [ -n "$qr_data" ]; then
    ./rabbitmqadmin publish routing_key=qrscan payload="$qr_data"
    echo "Sent: $qr_data"
  fi
done
```

---

## 3. Requirements (Bash Commands)

```bash
# Install RabbitMQ
sudo apt update
sudo apt install rabbitmq-server

# Install Python packages if using Python for consumer/producer
pip install pika requests

# Install Node.js and dependencies
sudo apt install nodejs npm
npm install axios

# Make sure the Flask app and RabbitMQ server are running:
python threat_analysis_app.py &
sudo systemctl start rabbitmq-server
```

---

## 4. Security & Production

- **Sanitize** QR code input before passing to subprocess
- **Run consumer as a service** (e.g., with systemd)
- **Implement error handling/logging** in scripts

---

## 5. Notes

- Update `/path/to/S500.js` to the actual script location.
- You may adjust message parsing for different operations (e.g., `--del` instead of `--add`).
- The Python scripts from the repo remain recommended for robustness, error handling, and richer logic.

---

## Example Service File (systemd)

To run the consumer as a background service:

```bash
sudo nano /etc/systemd/system/rabbitmq-consumer.service
```
```
[Unit]
Description=RabbitMQ Consumer for QR Threat Analysis

[Service]
ExecStart=/path/to/your/consumer_script.sh
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable rabbitmq-consumer
sudo systemctl start rabbitmq-consumer
```

---

**For further integration or PiCamera QR scan code, see the QR_SCAN repo or request additional details.**