import random
import string
from typing import Optional

from rich import print
from status import ContainerEntry, ContainerStatus, Role, Status

import docker

IP_NET = "10.5.5"  # Find a way to handle this better


def stop_all_containers(docker_client: docker.DockerClient):
    for container_entry in Status.get():
        container_entry = ContainerEntry.from_dict(container_entry)
        container = docker_client.containers.get(container_entry.container_id)
        print(f"[-] Stopping container {container_entry.container_name}...")
        container.stop()
        Status.remove_container_entry(container_entry)
        container_entry.status = ContainerStatus.STOPPED
        Status.add_container_entry(container_entry)


def start_all_containers(docker_client: docker.DockerClient):
    for container_entry in Status.get():
        container_entry = ContainerEntry.from_dict(container_entry)
        container = docker_client.containers.get(container_entry.container_id)
        print(f"[-] Starting container {container_entry.container_name}...")
        container.start()
        Status.remove_container_entry(container_entry)
        container_entry.status = ContainerStatus.RUNNING
        Status.add_container_entry(container_entry)


def create_container(docker_client: docker.DockerClient, role: Role, exposed_client_port: Optional[int] = None) -> tuple[str, str, dict]:
    identifier = "".join(random.choices(string.ascii_lowercase, k=8))
    name = f"home-tor-{role.lower()}-{identifier}"
    ip_addr = f"{IP_NET}.{Status.get_free_ip_octet()}"  # Handle max instead of infinite loop

    print(f"[-] Creating container {name}...")

    if exposed_client_port:
        host_config = docker_client.api.create_host_config(binds=["home-tor:/status"], port_bindings={9050: exposed_client_port})
    else:
        host_config = docker_client.api.create_host_config(binds=["home-tor:/status"])

    container = docker_client.api.create_container(
        image="home-tor",
        detach=True,
        name=name,
        environment={"ROLE": role.lower(), "NICK": f"{role.lower()}{identifier}"},
        volumes=["/status"],
        networking_config=docker_client.api.create_networking_config({"home-tor": docker_client.api.create_endpoint_config(ipv4_address=ip_addr)}),
        host_config=host_config,
        ports=[exposed_client_port] if exposed_client_port else None,
    )

    print(f"[-] Starting container...")
    docker_client.api.start(container["Id"])

    return name, ip_addr, container
