import ipaddress
import random
import string
from typing import Optional

from rich import print
from status import ContainerEntry, ContainerStatus, Role, Status

import docker

NUMBER_OF_FIRST_IPS_TO_EXCLUDE = 32


def stop_all_containers(docker_client: docker.DockerClient) -> None:
    for container_entry in Status.get():
        container_entry = ContainerEntry.from_dict(container_entry)
        container = docker_client.containers.get(container_entry.container_id)
        print(f"[-] Stopping container {container_entry.container_name}...")
        try:
            container.stop()
        except:
            print("[!] Failed to stop container, is it already stopped?")

        Status.remove_container_entry(container_entry)
        container_entry.status = ContainerStatus.STOPPED
        Status.add_container_entry(container_entry)


def start_all_containers(docker_client: docker.DockerClient) -> None:
    for container_entry in Status.get():
        container_entry = ContainerEntry.from_dict(container_entry)
        container = docker_client.containers.get(container_entry.container_id)
        print(f"[-] Starting container {container_entry.container_name}...")
        container.start()

        Status.remove_container_entry(container_entry)
        container_entry.status = ContainerStatus.RUNNING
        Status.add_container_entry(container_entry)


def create_container(
    docker_client: docker.DockerClient, role: Role, exposed_client_port: Optional[int] = None, extra_env_vars: dict = {}
) -> tuple[str, str, dict]:
    # Generate name
    identifier = "".join(random.choices(string.ascii_lowercase, k=8))
    name = f"testing-tor-{role.lower()}-{identifier}"

    # Find an available IP
    network = docker_client.networks.get("testing-tor")
    subnet = network.attrs["IPAM"]["Config"][0]["Subnet"]
    subnet = ipaddress.ip_network(subnet)
    first_ip = int(subnet.network_address) + NUMBER_OF_FIRST_IPS_TO_EXCLUDE
    last_ip = int(subnet.broadcast_address) - 1
    ip_addr = str(ipaddress.ip_address(random.randint(first_ip, last_ip)))
    while ip_addr in Status.get_used_ip_list():
        ip_addr = str(ipaddress.ip_address(random.randint(first_ip, last_ip)))

    # Setup ports
    if exposed_client_port:
        host_config = docker_client.api.create_host_config(binds=["testing-tor:/status"], port_bindings={9050: exposed_client_port})
    else:
        host_config = docker_client.api.create_host_config(binds=["testing-tor:/status"])

    # Create the container
    container = docker_client.api.create_container(
        image="testing-tor",
        detach=True,
        name=name,
        environment={"ROLE": role.lower(), "NICK": f"{role.lower()}{identifier}", **extra_env_vars},
        volumes=["/status"],
        networking_config=docker_client.api.create_networking_config({"testing-tor": docker_client.api.create_endpoint_config(ipv4_address=ip_addr)}),
        host_config=host_config,
        ports=[exposed_client_port] if exposed_client_port else None,
    )

    # Start the container
    docker_client.api.start(container["Id"])

    return name, str(ip_addr), container


def remove_container(docker_client: docker.DockerClient, container_entry: ContainerEntry, restart: bool = True):
    container = docker_client.containers.get(container_entry.container_name)

    if container_entry.role == Role.DA:
        container.exec_run("/opt/cleanup_da.sh")

    try:
        container.stop()
    except:
        print("[!] Failed to stop container, trying to remove it...")
    container.remove()

    Status.remove_container_entry(container_entry)

    if container_entry.role == Role.DA and restart:
        print(f"[-] Removing a DA requires restarting all nodes...")
        stop_all_containers(docker_client)
        start_all_containers(docker_client)
