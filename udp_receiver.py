
#!/usr/bin/env python3
import socket
import time
import argparse
import signal
import sys
from collections import defaultdict

def main():
    parser = argparse.ArgumentParser(description="UDP Traffic Receiver")
    parser.add_argument("-p", "--port", type=int, default=9999, help="Listen port (default: 9999)")
    parser.add_argument("-b", "--buffer", type=int, default=4096, help="Socket buffer size (default: 4096)")
    args = parser.parse_args()

    # Configuration
    listen_port = args.port
    buffer_size = args.buffer
    
    # Initialize statistics
    stats = {
        'start_time': time.time(),
        'packets_received': 0,
        'bytes_received': 0,
        'last_seq_num': None,
        'out_of_order': 0,
        'duplicates': 0,
        'missing': 0,
        'sequence_numbers': set(),
        'min_seq': None,
        'max_seq': None,
        'last_report_time': time.time(),
        'last_packets': 0,
        'last_bytes': 0,
        'one_sec_rates': []  # Store the last 10 seconds of rates
    }

    # Create UDP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024 * 1024 * 8)  # 8MB buffer
    sock.bind(('0.0.0.0', listen_port))
    sock.settimeout(1.0)  # 1 second timeout for reporting even when no packets arrive
    
    print(f"UDP receiver listening on port {listen_port}")
    print("Press Ctrl+C to stop and see final statistics")
    print("\nTime       | Packets/s   | Mbps        | Cumulative Loss %")
    print("-----------+-------------+-------------+----------------")

    def print_stats(stats, final=False):
        now = time.time()
        elapsed = now - stats['last_report_time']
        total_elapsed = now - stats['start_time']
        
        if elapsed > 0:
            pps = (stats['packets_received'] - stats['last_packets']) / elapsed
            bps = (stats['bytes_received'] - stats['last_bytes']) * 8 / elapsed
            # Store rate for averaging
            stats['one_sec_rates'].append((pps, bps))
            # Keep only the last 10 rates
            if len(stats['one_sec_rates']) > 10:
                stats['one_sec_rates'].pop(0)
        else:
            pps = 0
            bps = 0
        
        # Calculate average rates over the last 10 seconds
        if stats['one_sec_rates']:
            avg_pps = sum(rate[0] for rate in stats['one_sec_rates']) / len(stats['one_sec_rates'])
            avg_bps = sum(rate[1] for rate in stats['one_sec_rates']) / len(stats['one_sec_rates'])
        else:
            avg_pps = 0
            avg_bps = 0
        
        if stats['min_seq'] is not None and stats['max_seq'] is not None:
            expected = stats['max_seq'] - stats['min_seq'] + 1
            received = len(stats['sequence_numbers'])
            if expected > 0:
                loss_percent = 100 * (expected - received) / expected
            else:
                loss_percent = 0
        else:
            expected = 0
            loss_percent = 0
        
        if final:
            print("\n--- Final Statistics ---")
            print(f"Test duration: {total_elapsed:.2f} seconds")
            print(f"Total packets received: {stats['packets_received']}")
            print(f"Total bytes received: {stats['bytes_received']}")
            print(f"Average packet rate: {stats['packets_received']/total_elapsed if total_elapsed > 0 else 0:.2f} pps")
            print(f"Average bit rate: {stats['bytes_received']*8/total_elapsed/1_000_000 if total_elapsed > 0 else 0:.2f} Mbps")
            print(f"Sequence range: {stats['min_seq']} to {stats['max_seq']}")
            print(f"Expected packets: {expected}")
            print(f"Missing packets: {expected - received if expected > received else 0}")
            print(f"Duplicate packets: {stats['duplicates']}")
            print(f"Out-of-order packets: {stats['out_of_order']}")
            print(f"Packet loss: {loss_percent:.2f}%")
            # Show instantaneous rate history
            print("\nRate history (last 10 seconds):")
            for i, (rate_pps, rate_bps) in enumerate(stats['one_sec_rates']):
                print(f"  {total_elapsed-len(stats['one_sec_rates'])+i+1:.1f}s: {rate_pps:.2f} pps, {rate_bps/1_000_000:.2f} Mbps")
        else:
            # Format time as HH:MM:SS
            time_str = time.strftime("%H:%M:%S", time.localtime())
            # Print in a fixed-width format for better readability
            print(f"{time_str} | {pps:11.2f} | {bps/1_000_000:11.2f} | {loss_percent:14.2f}")
        
        stats['last_report_time'] = now
        stats['last_packets'] = stats['packets_received']
        stats['last_bytes'] = stats['bytes_received']

    def signal_handler(sig, frame):
        print_stats(stats, final=True)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        while True:
            try:
                data, addr = sock.recvfrom(buffer_size)
                stats['packets_received'] += 1
                stats['bytes_received'] += len(data)
                
                # Parse sequence number from packet
                try:
                    seq_str = data.split(b':')[0]
                    seq_num = int(seq_str)
                    
                    # Update sequence stats
                    if seq_num in stats['sequence_numbers']:
                        stats['duplicates'] += 1
                    else:
                        stats['sequence_numbers'].add(seq_num)
                    
                    # Track min/max sequence
                    if stats['min_seq'] is None or seq_num < stats['min_seq']:
                        stats['min_seq'] = seq_num
                    if stats['max_seq'] is None or seq_num > stats['max_seq']:
                        stats['max_seq'] = seq_num
                    
                    # Check for out-of-order
                    if stats['last_seq_num'] is not None and seq_num < stats['last_seq_num']:
                        stats['out_of_order'] += 1
                    
                    stats['last_seq_num'] = seq_num
                except:
                    # Couldn't parse sequence, just count the packet
                    pass
                
            except socket.timeout:
                # No data received in the timeout period
                pass
            
            # Print periodic stats
            now = time.time()
            if now - stats['last_report_time'] >= 1.0:
                print_stats(stats)
                
    except KeyboardInterrupt:
        print_stats(stats, final=True)
    finally:
        sock.close()

if __name__ == "__main__":
    main()

