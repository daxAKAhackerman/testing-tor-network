# Set the location of the HS files
HiddenServiceDir /var/lib/tor/.tor/hs/

# Tell TOR to redirect incoming TOR network requests on port 80 to port 80 on localhost
HiddenServicePort 80 127.0.0.1:80

# Disable the client port
SocksPort 0
