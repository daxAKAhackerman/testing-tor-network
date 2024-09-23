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
# By default we need an agreement of 2/3 DAs to reach consensus, so we'll create 3 DAs
# You can always add more, but if you want to go with less, you'll have to adjust the docker/torrc.da file using the AuthDirNumSRVAgreements directive
$ python cli/main.py add-da && python cli/main.py add-da && python cli/main.py add-da

# If you're lucky, all DAs will be added to the consensus under 5 minutes
# If you're not, about 20 minutes
# Note that in a real TOR network, this would take way longer
# Nyx is installed on every container and the control port is configured, so we can use it to monitor the progress
# First, find the name of your DA containers
$ python cli/main.py list-containers --filter "-da-"

# Then start Nyx in all of them and wait until they get the "Authority" flag
$ docker exec -it testing-tor-da-00000000 nyx

# Once that's done, let's add some relays
$ python cli/main.py add-relay && python cli/main.py add-relay && python cli/main.py add-relay && python cli/main.py add-relay && python cli/main.py add-relay
$ python cli/main.py add-exit && python cli/main.py add-exit && python cli/main.py add-exit

# Just like the DAs, you can use Nyx to monitor your nodes
# Normally, they should get their respective flags in under 5 minutes

# Let's add a hidden service
$ python cli/main.py add-hs

# And a client
# We'll specify which port on the host we want to bind to the client's SocksPort (9050)
# The port is optional, if you don't specify it we simply don't expose the port to the host
$ python cli/main.py add-client --port 9050

# Now let's find the onion address of our hidden service
# Find the container name, and then the HS hostname
$ python cli/main.py list-containers --filter "-hs-"
$ docker exec testing-tor-hs-00000000 cat /var/lib/tor/.tor/hs/hostname

# Finally, let's start a simple Web server on port 80 in the HS container
$ docker exec -it testing-tor-hs-00000000 bash
$ mkdir webroot
$ cd webroot
$ echo "<h1>Hello from my own TOR network!</h1>" > index.html
$ python3 -m http.server 80

# You can now configure any browser to use the SocksPort you specified when creating the client and you should be able to reach your python http server using the onion hostname from the HS container. 

# Congratulations, you are now the proud owner of a fully functional TOR testing network! 

# The CLI can also be used for a few routine operations such as:
$ python cli/main.py start-container # Starts the specified container
$ python cli/main.py stop-container # Stops the specified container
$ python cli/main.py delete-container # Delete the specified container
$ python cli/main.py start-network # Start every container in the network
$ python cli/main.py stop-network # Stop every container in the network
$ python cli/main.py restart-network # Stop, then start every container in the network
$ python cli/main.py delete-network # Delete every container in the network

# If you do some weird stuff that makes it impossible to use the delete-network command successfully, you can use the following command, which should do the trick
# You'll have to run `make` again after that since it basically deletes everything
$ make nuke -i
```

## Adding your own hidden service

Once you have a fully functional TOR testing network running, a next logical step could be to add your own hidden services. The one provided by the command `add-hs` is very basic and only exposes port 80, with no actual service running behind it. Adding your own service should be pretty straight forward. 

1. Create a Dockerfile containing your service
2. Install TOR in it. You can check the [Dockerfile](docker/Dockerfile), or even better [the official TOR documentation](https://community.torproject.org/onion-services/setup/install/).
3. Be sure to start the TOR service in your entrypoint or command
4. Populate your `/etc/tor/torrc` file. Fortunately, the CLI provides a command to give the directive you need: `python cli/main.py get-hs-info`. This will print the full torrc file that you need to put in your container in order for it to be able to connect to the TOR testing network. Note that you need to have a working network with a HS node for the command to work
5. Start your container using the correct network. An example command is also given by `python cli/main.py get-hs-info`. 

## You may also like...

- [XSS Catcher](https://github.com/daxAKAhackerman/XSS-Catcher) - A blind XSS detection and XSS data capture framework
- [Simple One Time Secret](https://github.com/daxAKAhackerman/simple-one-time-secret) - Generate single use, expiring links to share sensitive information

---

> GitHub [@daxAKAhackerman](https://github.com/daxAKAhackerman/)
