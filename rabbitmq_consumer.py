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