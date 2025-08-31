# rabbitmq
Integration of RabbitMQ into the demonstation

Cater for the passing of "http://localhost:5000/?query=OP7,S500" to threat_analysis_app.py

Cater for the passing of variables to JS files "node S500.js --add --db OP7" from location "C:\ies4-military-database-analysis\src\static\js"

**Goal:**
- Raspberry Pi scans a QR code using code from [QR_SCAN](https://github.dxc.com/ireid5/QR_SCAN)
- The QR data is sent as a message to RabbitMQ
- When RabbitMQ receives the message, it triggers:
  1. **A call to the SolrSim app** by appending the QR value (e.g., "OP7,S500") to `http://localhost:5000/?query=` -- so it’s a web request to the Flask app.
  2. **A Node.js script call** passing the same parameters, e.g., `node s500.js --add --db OP7` for the IES repo.

**Solution Overview:**
- You’ll need two main Python scripts:
  1. **RabbitMQ Consumer**: Listens for messages, triggers the Flask app via HTTP, and calls the Node.js script with subprocess.
  2. **QR Code Scanner/Producer**: Uses the QR_SCAN repo to scan and send messages to RabbitMQ.

---

## 1. RabbitMQ Consumer Script

This script:
- Listens to a queue (e.g., `qrscan`)
- Receives messages in the format `OP7,S500`
- Makes a GET request to `http://localhost:5000/?query=OP7,S500`
- Calls the Node.js script as `node s500.js --add --db OP7`

```
python name=rabbitmq_consumer.py
import pika
import requests
import subprocess
import sys
import os

# RabbitMQ setup
RABBITMQ_HOST = 'localhost'
RABBITMQ_QUEUE = 'qrscan'

# Flask app endpoint
FLASK_URL_BASE = "http://localhost:5000/?query="

# Path to Node.js script
NODE_SCRIPT_PATH = "/path/to/S500.js"  # <-- Update this!

def process_message(body):
    # Example message: 'OP7,S500'
    print(f"Received message: {body}")
    query_param = body.strip()
    # 1. Call Flask app via HTTP GET
    flask_url = FLASK_URL_BASE + query_param
    print(f"Calling Flask app: {flask_url}")
    try:
        resp = requests.get(flask_url)
        print(f"Flask response status: {resp.status_code}")
    except Exception as e:
        print(f"Error calling Flask app: {e}")

    # 2. Call Node.js script
    try:
        op_area, _ = query_param.split(',')
        node_cmd = [
            'node',
            NODE_SCRIPT_PATH,
            '--add',
            '--db',
            op_area
        ]
        print(f"Running Node script: {' '.join(node_cmd)}")
        result = subprocess.run(node_cmd, capture_output=True, text=True)
        print("Node script output:", result.stdout)
        if result.stderr:
            print("Node script error:", result.stderr)
    except Exception as e:
        print(f"Error running Node script: {e}")

def callback(ch, method, properties, body):
    process_message(body.decode())
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE)
    print("Waiting for messages...")
    channel.basic_consume(queue=RABBITMQ_QUEUE, on_message_callback=callback)
    channel.start_consuming()

if __name__ == "__main__":
    main()
```

---

## 2. QR Code Scanner Producer (using QR_SCAN)

Assuming you want a script that scans and sends to RabbitMQ:

```
python name=qrscan_producer.py
import pika
from qr_scan import scan_qr_code  # Adapt import as needed

RABBITMQ_HOST = 'localhost'
RABBITMQ_QUEUE = 'qrscan'

def send_to_rabbitmq(data):
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
    channel = connection.channel()
    channel.queue_declare(queue=RABBITMQ_QUEUE)
    channel.basic_publish(exchange='', routing_key=RABBITMQ_QUEUE, body=data)
    connection.close()
    print(f"Sent: {data}")

def main():
    while True:
        qr_data = scan_qr_code()  # This should return the QR code string like 'OP7,S500'
        if qr_data:
            send_to_rabbitmq(qr_data)

if __name__ == "__main__":
    main()
```

**Note:**  
- The `scan_qr_code` function should be adapted from your QR_SCAN repo (likely wraps OpenCV + PiCamera).
- You can change the queue names as needed.

---

## 3. Summary of Flow

1. **QR code scanned on Pi** → string like `OP7,S500`
2. **Producer script** sends this string to RabbitMQ
3. **Consumer script** listens for messages:
   - Calls Flask app: `http://localhost:5000/?query=OP7,S500`
   - Runs: `node S500.js --add --db OP7` for the IES repo

---

## 4. Requirements

- Install RabbitMQ (`sudo apt install rabbitmq-server`)
- Install Python packages: `pip install pika requests`
- Node.js and dependencies (`npm install axios`)
- Update `NODE_SCRIPT_PATH` in the consumer script to the correct path for your `S500.js`
- The Flask app (`threat_analysis_app.py`) and RabbitMQ server should be running

---

## 5. Security & Production

- Sanitize input from QR codes before passing to subprocess.
- Run the consumer script as a service if possible.
- Proper error handling/logging.

---

## 6. TLS Configuration
 - Step 1: Check the Current Configuration File
          First, let's see what's in your current configuration file:
```
cat /etc/rabbitmq/rabbitmq.conf
```
 - Step 2: Create a Minimal Working Configuration
          Let's start with a basic configuration that works, then gradually add SSL:
```
# Backup the current config
sudo cp /etc/rabbitmq/rabbitmq.conf /etc/rabbitmq/rabbitmq.conf.backup

# Create a minimal working configuration
sudo tee /etc/rabbitmq/rabbitmq.conf > /dev/null << 'EOF'
# Basic RabbitMQ Configuration
listeners.tcp.default = 5672

# Management Interface
management.tcp.port = 15672
EOF
```
 - Step 3: Test Basic Configuration
```
# Try to start RabbitMQ with basic config
sudo systemctl start rabbitmq-server
sudo systemctl status rabbitmq-server
```
 - If this works, you should see:
```
Active: active (running)
```
 - Step 4: Verify Basic Setup Works
```
# Check if ports are listening
sudo netstat -tlnp | grep -E ':(5672|15672)'

# Test HTTP management interface
curl http://192.168.0.130:15672
```
 - Step 5: Add SSL Configuration Gradually
          Once the basic configuration works, let's add SSL step by step:
```
# Create the SSL-enabled configuration
sudo tee /etc/rabbitmq/rabbitmq.conf > /dev/null << 'EOF'
# Basic AMQP Configuration
listeners.tcp.default = 5672
listeners.ssl.default = 5671

# Basic Management Interface
management.tcp.port = 15672

# SSL Configuration for AMQP
ssl_options.cacertfile = /etc/rabbitmq/certs/ca_root.pem
ssl_options.certfile = /etc/rabbitmq/certs/rabbitcert.pem
ssl_options.keyfile = /etc/rabbitmq/certs/rabbitkey.pem
ssl_options.verify = verify_none
ssl_options.fail_if_no_peer_cert = false
EOF
```
 - Step 6: Verify Certificate Files Exist
```
# Check if certificate files exist and have correct permissions
ls -la /etc/rabbitmq/certs/
sudo chown -R rabbitmq:rabbitmq /etc/rabbitmq/certs/
sudo chmod 600 /etc/rabbitmq/certs/rabbitkey.pem
sudo chmod 644 /etc/rabbitmq/certs/*.pem
```
 - Step 7: Restart and Test SSL AMQP
```
sudo systemctl restart rabbitmq-server
sudo systemctl status rabbitmq-server

# If successful, test SSL connection
openssl s_client -connect 192.168.0.130:5671
```
 - Step 8: Add HTTPS Management (Final Step)
          Only after the above works, add HTTPS management:
```
# Add HTTPS management to the configuration
sudo tee /etc/rabbitmq/rabbitmq.conf > /dev/null << 'EOF'
# Basic AMQP Configuration
listeners.tcp.default = 5672
listeners.ssl.default = 5671

# Management Interface
management.tcp.port = 15672
management.ssl.port = 15671

# SSL Configuration for AMQP
ssl_options.cacertfile = /etc/rabbitmq/certs/ca_root.pem
ssl_options.certfile = /etc/rabbitmq/certs/rabbitcert.pem
ssl_options.keyfile = /etc/rabbitmq/certs/rabbitkey.pem
ssl_options.verify = verify_none
ssl_options.fail_if_no_peer_cert = false

# Management SSL Configuration
management.ssl.cacertfile = /etc/rabbitmq/certs/ca_root.pem
management.ssl.certfile = /etc/rabbitmq/certs/rabbitcert.pem
management.ssl.keyfile = /etc/rabbitmq/certs/rabbitkey.pem
EOF
```
 - Step 9: Final Restart and Test
```
sudo systemctl restart rabbitmq-server
sudo systemctl status rabbitmq-server

# Test all endpoints
curl http://192.168.0.130:15672   # HTTP Management
curl -k https://192.168.0.130:15671  # HTTPS Management
```
---
The key points:

Use port 15671 for HTTPS management interface
Use port 15672 for HTTP management interface
---

If you want to run a different operation (e.g., `--del` instead of `--add`), you can adjust the message format and parsing logic.
