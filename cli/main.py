import json
import os
from typing import Optional

import typer
from container import (
    create_container,
    remove_container,
    start_all_containers,
    stop_all_containers,
)
from rich import print, print_json
from status import (
    STATUS_FILE,
    ContainerEntry,
    ContainerEntryNotFound,
    ContainerStatus,
    Role,
    Status,
)

import docker

app = typer.Typer()
network_app = typer.Typer()
container_app = typer.Typer()
app.add_typer(network_app, name="network", help="Commands to manage the network as a whole")
app.add_typer(container_app, name="container", help="Commands to manage containers")
docker_client = docker.from_env()


@container_app.command("add-da")
def add_da(count: int = typer.Option(1, help="Number of containers to create")):
    """
    Add a directory authority to the network
    """

    for i in range(0, count):
        print(f"[-] Adding new DA container...")
        name, ip_addr, container = create_container(docker_client, Role.DA)

        print(f"[-] Adding a new DA requires restarting all containers...")
        stop_all_containers(docker_client)
        start_all_containers(docker_client)

        container_entry = ContainerEntry(Role.DA, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
        Status.add_container_entry(container_entry)

        print(f"[+] Added new DA container {name}")


@container_app.command("add-relay")
def add_relay(count: int = typer.Option(1, help="Number of containers to create")):
    """
    Add a middle/guard relay to the network
    """

    for i in range(0, count):
        print(f"[-] Adding new middle/guard relay container...")
        name, ip_addr, container = create_container(docker_client, Role.RELAY)

        container_entry = ContainerEntry(Role.RELAY, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
        Status.add_container_entry(container_entry)

        print(f"[+] Added new middle/guard relay container {name}")


@container_app.command("add-exit")
def add_exit(count: int = typer.Option(1, help="Number of containers to create")):
    """
    Add an exit relay to the network
    """

    for i in range(0, count):
        print(f"[-] Adding new exit relay container...")
        name, ip_addr, container = create_container(docker_client, Role.EXIT)

        container_entry = ContainerEntry(Role.EXIT, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
        Status.add_container_entry(container_entry)

        print(f"[+] Added new exit relay container {name}")


@container_app.command("add-hs")
def add_hs(
    count: int = typer.Option(1, help="Number of containers to create"),
    hs_port: int = typer.Option(80, help="The port to for the hidden service to listen for requests"),
    service_ip: str = typer.Option("127.0.0.1", help="The IP address of the service"),
    service_port: int = typer.Option(80, help="The port of the service"),
):
    """
    Add a hidden service to the network.
    If no option is specified, it will forward any TOR traffic on port 80 to localhost port 80 by default.
    You can exec in the container and run something on that port to test it out.
    """

    for i in range(0, count):
        print(f"[-] Adding new hidden service container...")
        name, ip_addr, container = create_container(
            docker_client, Role.HS, extra_env_vars={"HS_PORT": hs_port, "SERVICE_IP": service_ip, "SERVICE_PORT": service_port}
        )

        container_entry = ContainerEntry(Role.HS, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
        Status.add_container_entry(container_entry)

        print(f"[+] Added new hidden service container {name}")


@container_app.command("add-client")
def add_client(
    count: int = typer.Option(1, help="Number of containers to create"), port: Optional[int] = typer.Option(None, help="TOR SOCKSv5 port to expose on the host")
):
    """
    Add a client to the network.
    You can use it as an entrypoint for your network.
    """

    for i in range(0, count):
        print(f"[-] Adding new client container...")
        name, ip_addr, container = create_container(docker_client, Role.CLIENT, exposed_client_port=port)

        container_entry = ContainerEntry(Role.CLIENT, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
        Status.add_container_entry(container_entry)

        print(f"[+] Added new client container {name}")


@container_app.command("stop")
def stop_container(name: str):
    """
    Stop (but not remove) a container
    """
    try:
        container_entry = Status.get_container_entry(name)
    except ContainerEntryNotFound:
        print(f"[!] Container {name} does not exist in status file")
        raise typer.Exit(1)
    else:
        container = docker_client.containers.get(name)

        print(f"[-] Stopping container {name}...")
        container.stop()

        Status.remove_container_entry(container_entry)
        container_entry.status = ContainerStatus.STOPPED
        Status.add_container_entry(container_entry)

        print(f"[+] Stopped container {name}")


@container_app.command("start")
def start_container(name: str):
    """
    Start an existing container
    """
    try:
        container_entry = Status.get_container_entry(name)
    except ContainerEntryNotFound:
        print(f"[!] Container {name} does not exist in status file")
        raise typer.Exit(1)
    else:
        container = docker_client.containers.get(name)

        print(f"[-] Starting container {name}...")
        container.start()

        Status.remove_container_entry(container_entry)
        container_entry.status = ContainerStatus.RUNNING
        Status.add_container_entry(container_entry)

        print(f"[+] Started container {name}")


@container_app.command("delete")
def delete_container(name: str):
    """
    Remove a container from the network and delete it
    """
    try:
        container_entry = Status.get_container_entry(name)
    except ContainerEntryNotFound:
        print(f"[!] Container {name} does not exist in status file")
        raise typer.Exit(1)
    else:
        print(f"[-] Removing container {name}")
        remove_container(docker_client, container_entry)


@container_app.command("list")
def list_containers(filter: Optional[str] = typer.Option(None, help="Will only print containers object that contain this string")):
    """
    Print the status file containing containers information.
    """
    status = Status.get()

    if filter:
        print_json(json.dumps([container_entry for container_entry in status if filter in json.dumps(container_entry)]))
    else:
        print_json(json.dumps(status))


@container_app.command("get-torrc")
def get_torrc(name: str):
    """
    Prints the torrc configuration of a container
    """
    container = docker_client.containers.get(name)

    exit_code, output = container.exec_run("cat /etc/tor/torrc")
    for line in output.decode().lstrip().split("\n"):
        if not line.startswith("#"):
            print(line)


@container_app.command("get-onion-domain")
def get_onion_domain(name: str):
    """
    Prints hidden service domain of a HS container
    """
    try:
        container_entry = Status.get_container_entry(name)
    except ContainerEntryNotFound:
        print(f"[!] Container {name} does not exist in status file")
        raise typer.Exit(1)
    else:
        if container_entry.role != Role.HS:
            print(f"[!] Container {name} is not a hidden service container")
            raise typer.Exit(1)

        container = docker_client.containers.get(name)

        exit_code, output = container.exec_run("cat /var/lib/tor/.tor/hs/hostname")
        for line in output.decode().lstrip().split("\n"):
            print(line)


@network_app.command("stop")
def stop_network():
    """
    Stop the whole network
    """
    print(f"[-] Stopping all containers...")
    stop_all_containers(docker_client)


@network_app.command("start")
def start_network():
    """
    Start all existing containers
    """
    print(f"[-] Starting all containers...")
    start_all_containers(docker_client)


@network_app.command("restart")
def restart_network():
    """
    Stop all containers, then start them again
    """
    print(f"[-] Restarting all containers...")
    stop_all_containers(docker_client)
    start_all_containers(docker_client)


@network_app.command("delete")
def delete_network():
    """
    Delete all containers, empty the docker volume and flush the status file
    """
    status = Status.get()
    for container_entry in status:
        print(f'Removing container {container_entry["container_name"]}')
        remove_container(docker_client, ContainerEntry.from_dict(container_entry), False)

    print("[-] Cleaning volume...")
    volume = docker_client.volumes.get("testing-tor")
    volume.remove()
    docker_client.volumes.create("testing-tor")

    print("[-] Deleting status file...")
    os.remove(STATUS_FILE)


if __name__ == "__main__":
    app()
