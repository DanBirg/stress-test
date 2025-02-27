
#!/usr/bin/env python3
import socket
import time
import sys
import argparse
import random

def main():
    parser = argparse.ArgumentParser(description="UDP Traffic Generator")
    parser.add_argument("target_ip", help="Target IP address")
    parser.add_argument("-p", "--port", type=int, default=9999, help="Target port (default: 9999)")
    parser.add_argument("-s", "--size", type=int, default=1400, help="Packet size in bytes (default: 1400)")
    parser.add_argument("-r", "--rate", type=int, default=1000, help="Packets per second (default: 1000)")
    parser.add_argument("-d", "--duration", type=int, default=60, help="Test duration in seconds (default: 60)")
    parser.add_argument("--random", action="store_true", help="Use random packet sizes (between 64 and specified size)")
    args = parser.parse_args()

    # Configuration
    target_ip = args.target_ip
    target_port = args.port
    packet_size = args.size
    packets_per_second = args.rate
    duration_seconds = args.duration
    use_random_size = args.random

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 1024 * 1024 * 8)  # 8MB buffer

    # Calculate intervals
    interval = 1.0 / packets_per_second
    end_time = time.time() + duration_seconds
    packets_sent = 0
    bytes_sent = 0
    last_report_time = time.time()
    last_packets_sent = 0
    last_bytes_sent = 0

    print(f"Sending traffic to {target_ip}:{target_port}")
    print(f"Target: {packets_per_second} packets/sec, Packet size: {packet_size} bytes")
    print(f"Duration: {duration_seconds} seconds")
    print("Press Ctrl+C to stop the test early")

    try:
        while time.time() < end_time:
            start = time.time()
            
            # Determine packet size for this packet
            if use_random_size:
                current_size = random.randint(64, packet_size)
            else:
                current_size = packet_size
                
            # Prepare packet data with sequence number
            packet_data = f"{packets_sent}:".encode() + b'X' * (current_size - len(f"{packets_sent}:") - 1)
            
            # Send packet
            sock.sendto(packet_data[:current_size], (target_ip, target_port))
            packets_sent += 1
            bytes_sent += current_size
            
            # Report statistics every second
            now = time.time()
            if now - last_report_time >= 1.0:
                elapsed = now - last_report_time
                pps = (packets_sent - last_packets_sent) / elapsed
                bps = (bytes_sent - last_bytes_sent) * 8 / elapsed
                print(f"Rate: {pps:.2f} pps, {bps/1_000_000:.2f} Mbps, Total: {packets_sent} packets")
                last_report_time = now
                last_packets_sent = packets_sent
                last_bytes_sent = bytes_sent
            
            # Sleep to maintain rate
            elapsed = time.time() - start
            if elapsed < interval:
                time.sleep(interval - elapsed)
                
    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        sock.close()
        duration = time.time() - (end_time - duration_seconds)
        print(f"\nTest summary:")
        print(f"Duration: {duration:.2f} seconds")
        print(f"Packets sent: {packets_sent}")
        print(f"Bytes sent: {bytes_sent}")
        print(f"Average packet rate: {packets_sent/duration:.2f} pps")
        print(f"Average bit rate: {bytes_sent*8/duration/1_000_000:.2f} Mbps")

if __name__ == "__main__":
    main()
