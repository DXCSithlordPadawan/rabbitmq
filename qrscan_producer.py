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