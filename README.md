# Testing TOR network
CLI tool to setup a testing TOR network with Docker

## Why

This repository was created out of curiosity about the TOR (The Onion Router) network. The goal was to understand how to manually setup a working testing network in a Docker environment and to experiment with different node configurations. The required knowledge to achieve this is spread thinly across the web and there are very few (if any) up to date example of how to do this. 

In this repository, I've added lots of comments in configuration files and shell scripts to explain why every line has to be in there. I've also added a Python CLI to ease the container management, but it is in no way required. If you want to setup your own TOR network based on the torrc files and docker entrypoint, go for it. 

## Installation

```bash
# The network 10.5.0.0/16 will be used by default. 
# If you don't like it, you can change it at the top of the Makefile

# Install the CLI dependencies using pipenv, build the Docker image and create the Docker volume and network
$ make

# The project uses pipenv and Python3.12 by default
# If this doesn't work for you, you can use the requirements.txt file and manage the virtual environment yourself
```

## Usage

```bash
# Source the venv
$ pipenv shell

# Show the help menu
$ python cli/main.py --help
```

## Complete example

The following will show you how to setup a testing TOR network comprised of 3 directory authorities, 5 mid/guard relays, 3 exit relays, 1 hidden service and 1 client. The client will expose the TOR SOCKSv5 to the host on port 9050 so that we can access the HS using a proxy configuration in the browser (I personally use a browser extension such as FoxyProxy). We will start a simple python http server to act as the HS. 

```bash
# Start by adding DAs
# We need an agreement of 2/3 DAs to reach consensus, so keep that in mind if you choose to spawn only 2 of them (might be harder to reach consensus)
$ python cli/main.py container add-da --count 3

# Let's add some relays
$ python cli/main.py container add-relay --count 5
$ python cli/main.py container add-exit --count 3

# Nyx is installed on every container and the control port is configured, so we can use it to monitor your nodes
# First, find the name of the node you want to monitor
$ python cli/main.py container list --filter "-da-"

# Then start Nyx
$ docker exec -it testing-tor-da-00000000 nyx

# To know if your DAs have been added to the consensus, check if they have the Authority flag using Nyx
# Same goes for the relays. Once they have their respective flags, it means they can be used to build circuits

# Let's add a hidden service
$ python cli/main.py container add-hs

# And a client
# We'll specify which port on the host we want to bind to the client's SocksPort (9050)
# The port is optional, if you don't specify it we simply don't expose the port to the host
$ python cli/main.py container add-client --port 9050

# Now let's find the onion address of our hidden service
# Find the container name, and then the HS hostname
$ python cli/main.py container list --filter "-hs-"
$ python cli/main.py container get-onion-domain testing-tor-hs-00000000

# Finally, let's start a simple Web server on port 80 in the HS container
$ docker exec -it testing-tor-hs-00000000 bash
$ mkdir webroot
$ cd webroot
$ echo "<h1>Hello from my own TOR network!</h1>" > index.html
$ python3 -m http.server 80

# You can now configure any browser to use the SocksPort you specified when creating the client and you should be able to reach your python http server using the onion hostname from the HS container. 

# Congratulations, you are now the proud owner of a fully functional TOR testing network! 

# The CLI can also be used for a few routine operations such as:
$ python cli/main.py container start # Starts the specified container
$ python cli/main.py container stop # Stops the specified container
$ python cli/main.py container delete # Delete the specified container
$ python cli/main.py network start # Start every container in the network
$ python cli/main.py network stop # Stop every container in the network
$ python cli/main.py network restart # Stop, then start every container in the network
$ python cli/main.py network delete # Delete every container in the network

# If you do some weird stuff that makes it impossible to use the delete-network command successfully, you can use the following command, which should do the trick
# You'll have to run `make` again after that since it basically deletes everything
$ make nuke -i
```

## Adding your own hidden service

Once you have a fully functional TOR testing network running, a next logical step could be to add your own hidden services. The one provided by the command `add-hs` is very basic and only exposes port 80 by default, with no actual service running behind it. Adding your own service can be achieved in multiple ways:

### Adding a container running only the service and have an HS node forward HS requests to it

This is by far the simplest way, if you don't mind the extra container and if your service doesn't exist yet. 

1. Choose an IP address for your service. By default, the CLI will always exclude the first 32 IP addresses of the subnet to assign IPs to the nodes, so choose an IP in this range (excluding `.0` and `.1` since they are used by Docker). If you need more than 30 IPs, you can adjust the `NUMBER_OF_FIRST_IPS_TO_EXCLUDE` variable in `cli/container.py`. 
2. Start your container using the correct network parameters: `docker run --network testing-tor --ip THE_IP_YOU_CHOSE mycontainer`.
3. Start an HS container specifying the information of your service: `python cli/main.py container add-hs --hs-port THE_PORT_TO_OPEN_TO_TOR --service-ip THE_IP_YOU_CHOSE --service-port THE_PORT_OF_YOUR_SERVICE`. Be sure that your service is listening on the correct interface (not just the loopback adapter). 

### Adding a second network interface to an existing container and have an HS node forward HS requests to it

This can be usefull if your container already exists and you don't want to recreate it. 

1. Choose an IP address for your service. By default, the CLI will always exclude the first 32 IP addresses of the subnet to assign IPs to the nodes, so choose an IP in this range (excluding `.0` and `.1` since they are used by Docker). If you need more than 30 IPs, you can adjust the `NUMBER_OF_FIRST_IPS_TO_EXCLUDE` variable in `cli/container.py`. 
2. If it's already running, stop your service container. 
3. Attach a new network interface to your service: `docker network connect --ip THE_IP_YOU_CHOSE testing-tor mycontainer`.
4. Start your service again.
5. Start an HS container specifying the information of your service: `python cli/main.py container add-hs --hs-port THE_PORT_TO_OPEN_TO_TOR --service-ip THE_IP_YOU_CHOSE --service-port THE_PORT_OF_YOUR_SERVICE`. Be sure that your service is listening on the correct interface (not just the loopback adapter or the original interface). 

### Adding a container running both the TOR HS and the service

This is a bit more complex, but if you are low on resources it can save you one container per HS. 

1. Create a Dockerfile containing your service
2. Install TOR in it. You can check the [Dockerfile](docker/Dockerfile), or even better [the official TOR documentation](https://community.torproject.org/onion-services/setup/install/).
3. Be sure to start the TOR service in your entrypoint or command
4. Populate your `/etc/tor/torrc` file. The CLI provides a command to give the directives you need: `python cli/main.py container get-hs-torrc <hs-container-name>`. This will print the full torrc file that you need to put in your container in order for it to be able to connect to the TOR testing network. You will probably need to adjust a few directives (ex: the port to forward the HS traffic to). Note that you need to have a working network with a HS node for the command to work. 
5. Choose an IP address for your service. By default, the CLI will always exclude the first 32 IP addresses of the subnet to assign IPs to the nodes, so choose an IP in this range (excluding `.0` and `.1` since they are used by Docker). If you need more than 30 IPs, you can adjust the `NUMBER_OF_FIRST_IPS_TO_EXCLUDE` variable in `cli/container.py`. 
6. Start your container using the correct network (ex: `docker start --network testing-tor --ip THE_IP_YOU_CHOSE mycontainer`).

## You may also like...

- [XSS Catcher](https://github.com/daxAKAhackerman/XSS-Catcher) - A blind XSS detection and XSS data capture framework
- [Simple One Time Secret](https://github.com/daxAKAhackerman/simple-one-time-secret) - Generate single use, expiring links to share sensitive information

---

> GitHub [@daxAKAhackerman](https://github.com/daxAKAhackerman/)
