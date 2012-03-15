#!/bin/sh
./cli/.libs/ibcli  --config ../etc/ironbee/ironbee-cli.conf --request-file ../data/skip2/skipfishVmoth.pcap-03198-192.168.2.3-40315-192.168.2.6-80.request.0000.raw --response-file ../data/skip2/skipfishVmoth.pcap-03198-192.168.2.3-40315-192.168.2.6-80.response.0000.raw --dump tx-full
