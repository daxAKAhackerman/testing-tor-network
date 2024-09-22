#!/bin/bash

BOOTSTRAP_FLAG=/bootstrapped
TOR_DIR=/var/lib/tor/.tor
KEYS_DIR=${TOR_DIR}/keys

if [[ -z "${ROLE}" ]]; then
    echo "No role defined, did you set the ROLE environment variable properly?"
    exit 1
fi

function bootstrap {
    IP_ADDR=$(ip route get 1.1.1.1 | head -n 1 | cut -d " " -f 7)
    echo IP address is ${IP_ADDR}

    cp /opt/torrc.base /etc/tor/torrc

    case $ROLE in
    da)
        echo "Setting up node as a directory authority"
        echo Nickname is ${NICK}
        echo Nickname ${NICK} >>/etc/tor/torrc
        echo Address ${IP_ADDR} >>/etc/tor/torrc
        echo "ContactInfo ${NICK} <${NICK} AT localhost>" >>/etc/tor/torrc
        cat /opt/torrc.da >>/etc/tor/torrc
        cd ${KEYS_DIR}
        echo $(tr -dc A-Za-z0-9 </dev/urandom | head -c 12) | sudo -u debian-tor tor-gencert --create-identity-key -m 12 -a ${IP_ADDR}:80 --passphrase-fd 0
        cd ${TOR_DIR}
        sudo -u debian-tor tor --list-fingerprint --dirauthority "placeholder 127.0.0.1:80 0000000000000000000000000000000000000000"

        AUTH_CERT=$(grep "fingerprint" ${KEYS_DIR}/authority_certificate | cut -d " " -f 2)
        FINGERPRINT=$(cat ${TOR_DIR}/fingerprint | cut -d " " -f 2)

        touch /var/lib/tor/.tor/{approved-routers,sr-state}
        chown debian-tor:debian-tor /var/lib/tor/.tor/{approved-routers,sr-state}

        echo "DirAuthority ${NICK} orport=9001 no-v2 v3ident=$AUTH_CERT ${IP_ADDR}:80 $FINGERPRINT" >>/status/dir-authorities
        ;;
    relay)
        echo "Setting up node as a guard/mid relay"
        echo Nickname is ${NICK}
        echo Nickname ${NICK} >>/etc/tor/torrc
        echo Address ${IP_ADDR} >>/etc/tor/torrc
        echo "ContactInfo ${NICK} <${NICK} AT localhost>" >>/etc/tor/torrc
        cat /opt/torrc.relay >>/etc/tor/torrc
        ;;
    exit)
        echo "Setting up node as an exit relay"
        echo Nickname is ${NICK}
        echo Nickname ${NICK} >>/etc/tor/torrc
        echo Address ${IP_ADDR} >>/etc/tor/torrc
        echo "ContactInfo ${NICK} <${NICK} AT localhost>" >>/etc/tor/torrc
        cat /opt/torrc.exit >>/etc/tor/torrc
        ;;
    client)
        echo "Setting up node as a client"
        cat /opt/torrc.client >>/etc/tor/torrc
        ;;
    hs)
        echo "Setting up node as a hidden service"
        cat /opt/torrc.hs >>/etc/tor/torrc
        ;; 
    *)
        echo "Unknown node type, exiting"
        exit 1
        ;;
    esac

    touch ${BOOTSTRAP_FLAG}
}

if [ ! -f ${BOOTSTRAP_FLAG} ]; then
    bootstrap
fi

while [[ ! -f "/status/dir-authorities" || "$(grep DirAuthority /status/dir-authorities | wc -l)" -lt "3" ]]; do
    echo Waiting for at least 3 directory authorities to come up...
    sleep 30
done

cat /status/dir-authorities >> /etc/tor/torrc
sort -uo /etc/tor/torrc /etc/tor/torrc

if [[ ! -z "$@" ]]; then
    exec $@
else
    sudo -u debian-tor tor
fi
