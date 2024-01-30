import socket
import sys
import threading
import time
import os

PACKET_SIZE = 500
RECEIVER_ADDR = ''
RECEIVER_PORT = ''
SENDER_ADDR = ''
SENDER_PORT = ''
SLEEP_INTERVAL = 0.05
TIMEOUT_INTERVAL = 0
WINDOW_SIZE = 0
FILE = ''
START_TIME = time.time()

base = 0
lock = threading.Lock()
send_timer = 0
duplicated = 0

class Timer:
    IS_TIMER_STOP = -1

    def __init__(self, duration):
        self._start_time = self.IS_TIMER_STOP
        self._duration = duration

    def start(self):
        if self._start_time == self.IS_TIMER_STOP:
            self._start_time = time.time()

    def stop(self):
        if self._start_time != self.IS_TIMER_STOP:
            self._start_time = self.IS_TIMER_STOP

    def timeout(self):
        if self._start_time == self.IS_TIMER_STOP:
            return False
        return time.time() - self._start_time >= self._duration

""" def get_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    send_ip = '127.0.0.1'
    send_port = 6000
    sock.bind((send_ip, send_port))
    return sock """

def utf8len(sock):
    return len(sock.encode('utf-8'))

def parse_args():
    global RECEIVER_ADDR
    global RECEIVER_PORT
    global SENDER_ADDR
    global SENDER_PORT
    global TIMEOUT_INTERVAL
    global WINDOW_SIZE
    global FILE
    global send_timer

    RECEIVER_ADDR = sys.argv[1]
    RECEIVER_PORT = int(sys.argv[2])
    SENDER_ADDR = "127.0.0.1"
    SENDER_PORT = int(sys.argv[3])
    WINDOW_SIZE = int(sys.argv[4])
    TIMEOUT_INTERVAL = float(sys.argv[5])
    FILE = sys.argv[6]
    send_timer = Timer(TIMEOUT_INTERVAL)

def pack(seq_num, data=b''):
    seq_bytes = seq_num.to_bytes(4, byteorder='little', signed=True)
    return seq_bytes + data

def empty_pkt():
    return b''

def unpack(packet):
    seq_num = int.from_bytes(packet[0:4], byteorder='little', signed=True)
    return seq_num, packet[4:]

def make_pkts(file):
    packets = []
    seq_num = 0
    while True:
        data = file.read(PACKET_SIZE)
        if not data:
            break
        packets.append(pack(seq_num, data))
        seq_num += 1
    return packets

def set_window_size(num_packets):
    global base
    return min(WINDOW_SIZE, num_packets - base)

def send_file(sock):
    global lock
    global base
    global send_timer
    global FILE
    global duplicated

    try:
        with open(FILE, 'rb') as file:
            packets = make_pkts(file)
            num_packets = len(packets)
            window_size = set_window_size(num_packets)
            next_to_send = 0
            base = 0

            threading.Thread(target=receive, args=(sock,)).start()

            while base < num_packets:
                lock.acquire()
                while next_to_send < base + window_size:
                    print(str(round(time.time() - START_TIME, 3)) + "   pkt: " + str(next_to_send) + "  Sender -> Receiver")
                    sock.sendto(packets[next_to_send], (RECEIVER_ADDR, RECEIVER_PORT))
                    next_to_send += 1
                    if next_to_send > (len(packets) - 1):
                        break

                if not send_timer._start_time != send_timer.IS_TIMER_STOP:
                    send_timer.start()

                while send_timer._start_time != send_timer.IS_TIMER_STOP and not send_timer.timeout():
                    lock.release()
                    time.sleep(SLEEP_INTERVAL)
                    lock.acquire()

                if send_timer.timeout():
                    print(str(round(time.time() - START_TIME, 3)) + "   pkt: " + str(next_to_send) + "  | Timeout since " + str(round(time.time() - START_TIME - TIMEOUT_INTERVAL, 3)))
                    send_timer.stop()
                    next_to_send = base

                if duplicated >= 3:
                    print(str(round(time.time() - START_TIME, 3)) + "   pkt: " + str(next_to_send - 1) + "  | 3 duplicated ACKs")
                    send_timer.stop()
                    next_to_send = base - 1
                    duplicated = 0

                else:
                    window_size = set_window_size(num_packets)
                lock.release()
                            
        sock.sendto(empty_pkt(), (RECEIVER_ADDR, RECEIVER_PORT))
        print("\n\n" + FILE + " is successfully transferred.")
        print("Throughput: " + str(round((os.path.getsize(FILE)) / round(time.time() - START_TIME, 3), 3)) + " pkts / sec")

    except IOError:
        print("Error opening " + FILE)
    

def receive(sock):
    global lock
    global base
    global send_timer
    global duplicated
    past_ack = -1

    while True:
        try:
            pkt, _ = sock.recvfrom(1024)
            ack, _ = unpack(pkt)

            lock.acquire()
            print(str(round(time.time() - START_TIME, 3)) + "   ack: " + str(ack) + "  Sender <- Receiver")
            if past_ack == ack:
                duplicated += 1
            elif ack >= base:
                base = ack + 1
                past_ack = ack
                send_timer.stop()
            lock.release()
        except OSError as e:
            if e.errno == 10038:  # WinError 10038: An operation was attempted on something that is not a socket
                break  # Ignore this specific error and continue the loop
            else:
                raise  # Re-raise any other OSError

def send_file_name(sock):
    global FILE
    if os.path.isfile(FILE):
        length = utf8len(FILE)
        sock.sendto(length.to_bytes(4, byteorder='big'), (RECEIVER_ADDR, RECEIVER_PORT))
        sock.sendto(bytes(FILE, 'UTF-8'), (RECEIVER_ADDR, RECEIVER_PORT))
        sock.sendto(bytes(str(os.path.getsize(FILE)), 'UTF-8'), (RECEIVER_ADDR, RECEIVER_PORT))
    else:
        sys.exit(FILE + " wasn't found in the directory!")


def main():
    parse_args()
    senderS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    senderS.bind((SENDER_ADDR, SENDER_PORT))
    print("Receiver IP address: " + RECEIVER_ADDR)
    print("Window size: " + str(WINDOW_SIZE))
    print("Timeout (sec): " + str(TIMEOUT_INTERVAL))
    print("File name: " + FILE )
    print("File Size: " + str(os.path.getsize(FILE)) + " Bytes \n\n" )
   

   
    send_file_name(senderS)
    send_file(senderS)
    senderS.close()
   
if __name__ == "__main__":
    main()
