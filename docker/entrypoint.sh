#!/bin/bash

BOOTSTRAP_FLAG=/bootstrapped
TOR_DIR=/var/lib/tor/.tor
KEYS_DIR=${TOR_DIR}/keys

TORRC=/etc/tor/torrc
TORRC_BASE=/opt/torrc.base
TORRC_DA=/opt/torrc.da
TORRC_RELAY=/opt/torrc.relay
TORRC_EXIT=/opt/torrc.exit
TORRC_CLIENT=/opt/torrc.client
TORRC_HS=/opt/torrc.hs
STATUS_AUTHORITIES=/status/dir-authorities

if [[ -z "${ROLE}" ]]; then
    echo "No role defined, did you set the ROLE environment variable properly?"
    exit 1
fi

function bootstrap {
    # Get the ip address that is attached to the interface linked to the default route
    IP_ADDR=$(ip route get 1.1.1.1 | head -n 1 | cut -d " " -f 7)
    echo IP address is ${IP_ADDR}

    cp ${TORRC_BASE} ${TORRC}

    case $ROLE in
    da)
        # Nickname is required, Address is kinda required (without it TOR seems to be unable to guess the IP in the testing network)
        # and ContactInfo is here to silence a warning
        echo "Setting up node as a directory authority"
        echo Nickname is ${NICK}
        echo Nickname ${NICK} >>${TORRC}
        echo Address ${IP_ADDR} >>${TORRC}
        echo "ContactInfo ${NICK} <${NICK} AT localhost>" >>${TORRC}
        cat ${TORRC_DA} >>${TORRC}
        cd ${KEYS_DIR}

        # The cert needs to be password encrypted, so generating a random string (since there is no reason to know it in this context)
        # Set cert validity for 12 months
        echo $(tr -dc A-Za-z0-9 </dev/urandom | head -c 12) | sudo -u debian-tor tor-gencert --create-identity-key -m 12 -a ${IP_ADDR}:80 --passphrase-fd 0

        cd ${TOR_DIR}
        # This generates the fingerprint files. The --dirauthority is required here because without it tor will fail and say that you
        # must have DirAuthority statements in your torrc file if TestingTorNetwork is set. The value doesn't matter though.
        sudo -u debian-tor tor --list-fingerprint --dirauthority "placeholder 127.0.0.1:80 0000000000000000000000000000000000000000"

        AUTH_CERT_FINGERPRINT=$(grep "fingerprint" ${KEYS_DIR}/authority_certificate | cut -d " " -f 2)
        SERVER_FINGERPRINT=$(cat ${TOR_DIR}/fingerprint | cut -d " " -f 2)

        # Those lines silence some TOR warnings
        touch ${TOR_DIR}/{approved-routers,sr-state}
        chown debian-tor:debian-tor ${TOR_DIR}/{approved-routers,sr-state}

        # The dir-authorities is mounted in all containers of this project. Real DAs are baked in the TOR executable, so to use our own in our
        # testing network, all torrc files need to have this line (one per DA)
        echo "DirAuthority ${NICK} orport=9001 no-v2 v3ident=$AUTH_CERT_FINGERPRINT ${IP_ADDR}:80 $SERVER_FINGERPRINT" >>${STATUS_AUTHORITIES}
        ;;
    relay)
        echo "Setting up node as a guard/mid relay"
        echo Nickname is ${NICK}
        echo Nickname ${NICK} >>${TORRC}
        echo Address ${IP_ADDR} >>${TORRC}
        echo "ContactInfo ${NICK} <${NICK} AT localhost>" >>${TORRC}
        cat ${TORRC_RELAY} >>${TORRC}
        ;;
    exit)
        echo "Setting up node as an exit relay"
        echo Nickname is ${NICK}
        echo Nickname ${NICK} >>${TORRC}
        echo Address ${IP_ADDR} >>${TORRC}
        echo "ContactInfo ${NICK} <${NICK} AT localhost>" >>${TORRC}
        cat ${TORRC_EXIT} >>${TORRC}
        ;;
    client)
        echo "Setting up node as a client"
        cat ${TORRC_CLIENT} >>${TORRC}
        ;;
    hs)
        echo "Setting up node as a hidden service"
        cat ${TORRC_HS} >>${TORRC}
        if [[ -z "${HS_PORT}" ]]; then
            HS_PORT="80"
        fi
        if [[ -z "${SERVICE_PORT}" ]]; then
            SERVICE_PORT="80"
        fi
        if [[ -z "${SERVICE_IP}" ]]; then
            SERVICE_IP="127.0.0.1"
        fi
        echo HiddenServicePort ${HS_PORT} ${SERVICE_IP}:${SERVICE_PORT} >>${TORRC}
        ;;
    *)
        echo "Unknown node type, exiting"
        exit 1
        ;;
    esac

    # To prevent bootstrap from running more than once
    touch ${BOOTSTRAP_FLAG}
}

if [ ! -f ${BOOTSTRAP_FLAG} ]; then
    bootstrap
fi

# Add all the DirAuthority statements to torrc (and ensure no duplicate)
cat ${STATUS_AUTHORITIES} >>${TORRC}
sort -uo ${TORRC} ${TORRC}

# If a Docker CMD is specify, run it. Else, boot TOR!
if [[ ! -z "$@" ]]; then
    exec $@
else
    sudo -u debian-tor tor -f /etc/tor/torrc
fi
