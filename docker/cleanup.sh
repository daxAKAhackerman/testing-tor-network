#!/bin/bash

TOR_DIR=/var/lib/tor/.tor

FINGERPRINT=$(cat ${TOR_DIR}/fingerprint | cut -d " " -f 2)

grep -v ${FINGERPRINT} /status/dir-authorities >/status/dir-authorities.tmp
cp /status/dir-authorities.tmp /status/dir-authorities
