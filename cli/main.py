import json
import time
from typing import Optional

import typer
from container import create_container, start_all_containers, stop_all_containers
from rich import print, print_json
from status import ContainerEntry, ContainerEntryNotFound, ContainerStatus, Role, Status

import docker

app = typer.Typer()
docker_client = docker.from_env()


@app.command()
def add_da():
    name, ip_addr, container = create_container(docker_client, Role.DA)

    print(f"[-] Waiting 10 seconds to give time to new DA to genenerate keys...")
    time.sleep(10)  # Find a way to avoid waiting

    container_entry = ContainerEntry(Role.DA, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[-] Adding a new DA requires restarting all nodes...")
    stop_all_containers(docker_client)
    start_all_containers(docker_client)

    print(f"[+] Added new DA container {name}")


@app.command()
def add_relay():
    name, ip_addr, container = create_container(docker_client, Role.RELAY)

    container_entry = ContainerEntry(Role.RELAY, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new guard/middle relay container {name}")


@app.command()
def add_exit():
    name, ip_addr, container = create_container(docker_client, Role.EXIT)

    container_entry = ContainerEntry(Role.EXIT, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new exit relay container {name}")


@app.command()
def add_hs():
    name, ip_addr, container = create_container(docker_client, Role.HS)

    container_entry = ContainerEntry(Role.HS, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new hidden service container {name}")


@app.command()
def add_client(port: Optional[int] = typer.Option(None, help="TOR SOCKSv5 port to expose on the host")):
    name, ip_addr, container = create_container(docker_client, Role.CLIENT, exposed_client_port=port)

    container_entry = ContainerEntry(Role.CLIENT, name, container["Id"], status=ContainerStatus.RUNNING, ip_addr=ip_addr)
    Status.add_container_entry(container_entry)

    print(f"[+] Added new client container {name}")


@app.command()
def stop_container(name: str):
    try:
        container_entry = Status.get_container_entry(name)
    except ContainerEntryNotFound:
        print(f"[!] Container {name} does not exist in status")
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
    try:
        container_entry = Status.get_container_entry(name)
    except ContainerEntryNotFound:
        print(f"[!] Container {name} does not exist in status")
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
    try:
        container_entry = Status.get_container_entry(name)
    except ContainerEntryNotFound:
        print(f"[!] Container {name} does not exist in status")
        raise typer.Exit(1)
    else:
        container = docker_client.containers.get(name)

        if container_entry.role == Role.DA:
            print(f"[-] Running cleanup script...")
            container.exec_run("/opt/cleanup.sh")
        print(f"[-] Stopping container {name}...")
        container.stop()
        print(f"[-] Removing container {name}...")
        container.remove()

        Status.remove_container_entry(container_entry)

        if container_entry.role == Role.DA:
            print(f"[-] Removing a DA requires restarting all nodes...")
            stop_all_containers(docker_client)
            start_all_containers(docker_client)


@app.command()
def list_containers(filter: Optional[str] = typer.Option(None)):
    status = Status.get()

    if filter:
        print_json(json.dumps([container_entry for container_entry in status if filter in json.dumps(container_entry)]))
    else:
        print_json(json.dumps(status))


@app.command()
def stop_network():
    print(f"[-] Stopping all containers...")
    stop_all_containers(docker_client)


@app.command()
def start_network():
    print(f"[-] Starting all containers...")
    start_all_containers(docker_client)


@app.command()
def restart_network():
    print(f"[-] Stopping all containers...")
    stop_all_containers(docker_client)
    print(f"[-] Starting all containers...")
    start_all_containers(docker_client)


@app.command()
def get_hs_info():
    status = Status.get()

    for container_entry in status:
        container_entry = ContainerEntry.from_dict(container_entry)
        if container_entry.role == Role.HS:
            container = docker_client.containers.get(container_entry.container_id)

            exit_code, output = container.exec_run("cat /etc/tor/torrc")
            print("### BASE TORRC FILE TO USE ###")
            print(output.decode())
            print("### BASE DOCKER COMMAND TO RUN ###")
            print("$ docker run -d --name home-tor-hs-myservicename -e ROLE=hs -e NICK=hsmyservicename -v home-tor:/status --network home-tor home-tor\n")

            raise typer.Exit(0)

    print(f"[!] Could not find any HS to use as a model, did you add at least one HS to your net?")
    raise typer.Exit(1)


if __name__ == "__main__":
    app()
