FROM debian:12.7

ENV DEBIAN_FRONTEND=noninteractive

# Most of these are installed for debugging purposes
RUN apt-get update && apt-get install apt-transport-https wget gpg iproute2 iputils-ping sudo vim procps bash-completion curl -y
COPY tor.list /etc/apt/sources.list.d/tor.list
RUN wget -qO- https://deb.torproject.org/torproject.org/A3C4F0F979CAA22CDBA8F512EE8CBC9E886DDD89.asc | gpg --dearmor | tee /usr/share/keyrings/deb.torproject.org-keyring.gpg >/dev/null
RUN apt-get update && apt-get install tor deb.torproject.org-keyring nyx -y

# The following few lines silence a couple of TOR warnings
RUN mkdir -p /var/lib/tor/.tor/keys/
RUN chown -R debian-tor:debian-tor /var/lib/tor/.tor/
RUN chmod 2700 /var/lib/tor/.tor/
RUN chmod 2700 /var/lib/tor/.tor/keys/

COPY entrypoint.sh /opt/entrypoint.sh
COPY cleanup_da.sh /opt/cleanup_da.sh
COPY torrc.* /opt/
RUN chmod +x /opt/entrypoint.sh
RUN chmod +x /opt/cleanup_da.sh

ENTRYPOINT ["/bin/bash", "/opt/entrypoint.sh"]
