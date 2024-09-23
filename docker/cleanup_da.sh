#!/bin/bash

TOR_DIR=/var/lib/tor/.tor
DIR_AUTHORITIES_FILE=/status/dir-authorities

FINGERPRINT=$(cat ${TOR_DIR}/fingerprint | cut -d " " -f 2)

# Remove the DA's fingerprint from the status file
grep -v ${FINGERPRINT} ${DIR_AUTHORITIES_FILE} >${DIR_AUTHORITIES_FILE}.tmp
cp ${DIR_AUTHORITIES_FILE}.tmp ${DIR_AUTHORITIES_FILE}
