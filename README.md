## How to Use:

#### On the receiving server:
```
~/udp_receiver.py -p 9999
```
The receiver will listen to udp port 9999

#### On the sending client: 
```
~/udp_sender.py SERVER_IP_ADDRESS -p 9999 -r 1000 -d 60
```
The sender will sent udp port 9999, it will do 1000 PPS for 60 seconds
