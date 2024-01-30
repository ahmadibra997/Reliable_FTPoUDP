RECEIVER_CMD = python Receiver.py 0.05
SENDER_CMD = python Sender/Sender.py 127.0.0.1 6500 6000 10 1 Sender/medium.txt

.PHONY: run-receiver run-sender run-both

run-receiver:
	@start cmd /k "$(RECEIVER_CMD)"

run-sender:
	@start cmd /k "$(SENDER_CMD)"

run-both: run-receiver run-sender