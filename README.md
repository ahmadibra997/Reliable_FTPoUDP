# RUDP_FTP
In this project:

Implementation of Go-Back-N algorithm for a reliable UDP file transfer protocol.

## To run

* Run the receiver:
`python Receiver.py <loss-probability>`
* Run the sender:
`python Sender.py <receiver-ip> <receiver-port> <sender-port> <window-size> <timeout> <file-to-send>`
