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
docker_client = docker.from_env()


@app.command()
def add_da():
    """
    Add a directory authority to the network
    """

    print(f"[-] Adding new DA container...")
    name, ip_addr, container = create_container(docker_client, Role.DA)

    print(f"[-] Adding a new DA requires restarting all nodes...")
    stop_all_containers(docker_client)
    start_all_containers(docker_client)

    container_entry = ContainerEntry(Role.DA, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new DA container {name}")


@app.command()
def add_relay():
    """
    Add a middle/guard relay to the network
    """

    print(f"[-] Adding new middle/guard relay container...")
    name, ip_addr, container = create_container(docker_client, Role.RELAY)

    container_entry = ContainerEntry(Role.RELAY, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new middle/guard relay container {name}")


@app.command()
def add_exit():
    """
    Add an exit relay to the network
    """

    print(f"[-] Adding new exit relay container...")
    name, ip_addr, container = create_container(docker_client, Role.EXIT)

    container_entry = ContainerEntry(Role.EXIT, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new exit relay container {name}")


@app.command()
def add_hs(
    hs_port: Optional[int] = typer.Option(80, help="The port to for the hidden service to listen for requests"),
    service_ip: Optional[str] = typer.Option("127.0.0.1", help="The IP address of the service"),
    service_port: Optional[int] = typer.Option(80, help="The port of the service"),
):
    """
    Add a hidden service to the network.
    It will forward any TOR traffic on port 80 to localhost port 80.
    You can exec in the container and run something on that port to test it out.
    """

    print(f"[-] Adding new hidden service container...")
    name, ip_addr, container = create_container(
        docker_client, Role.HS, extra_env_vars={"HS_PORT": hs_port, "SERVICE_IP": service_ip, "SERVICE_PORT": service_port}
    )

    container_entry = ContainerEntry(Role.HS, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new hidden service container {name}")


@app.command()
def add_client(port: Optional[int] = typer.Option(None, help="TOR SOCKSv5 port to expose on the host")):
    """
    Add a client to the network.
    You can use it as an entrypoint for your network.
    """

    print(f"[-] Adding new client container...")
    name, ip_addr, container = create_container(docker_client, Role.CLIENT, exposed_client_port=port)

    container_entry = ContainerEntry(Role.CLIENT, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new client container {name}")


@app.command()
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


@app.command()
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


@app.command()
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


@app.command()
def list_containers(filter: Optional[str] = typer.Option(None, help="Will only print containers object that contain this string")):
    """
    Print the status file containing containers information.
    """
    status = Status.get()

    if filter:
        print_json(json.dumps([container_entry for container_entry in status if filter in json.dumps(container_entry)]))
    else:
        print_json(json.dumps(status))


@app.command()
def stop_network():
    """
    Stop the whole network
    """
    print(f"[-] Stopping all containers...")
    stop_all_containers(docker_client)


@app.command()
def start_network():
    """
    Start all existing containers
    """
    print(f"[-] Starting all containers...")
    start_all_containers(docker_client)


@app.command()
def restart_network():
    """
    Stop all containers, then start them again
    """
    print(f"[-] Restarting all containers...")
    stop_all_containers(docker_client)
    start_all_containers(docker_client)


@app.command()
def get_hs_torrc():
    """
    If you want to create your own container running a hidden service and attach it to the network, this command
    will give you an example of a working torrc file that you can use, as well as a sample Docker command to start
    your HS container. Note that we do not keep track of the IP addresses of these services, so collision is technically
    possible (but very unlikely).
    """
    status = Status.get()

    for container_entry in status:
        container_entry = ContainerEntry.from_dict(container_entry)
        if container_entry.role == Role.HS:
            container = docker_client.containers.get(container_entry.container_id)

            exit_code, output = container.exec_run("cat /etc/tor/torrc")
            for line in output.decode().lstrip().split("\n"):
                if not line.startswith("#"):
                    print(line)

            raise typer.Exit(0)

    print(f"[!] Could not find any HS to use as an example, did you add at least one HS to your network?")
    raise typer.Exit(1)


@app.command()
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
