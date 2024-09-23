import json
import os
import pathlib
from dataclasses import dataclass
from enum import StrEnum

STATUS_FILE = str(pathlib.Path(__file__).parent.resolve()) + "/status.json"


class ContainerEntryNotFound(Exception):
    pass


class ContainerStatus(StrEnum):
    RUNNING = "RUNNING"
    STOPPED = "STOPPED"


class Role(StrEnum):
    DA = "DA"
    RELAY = "RELAY"
    EXIT = "EXIT"
    CLIENT = "CLIENT"
    HS = "HS"


@dataclass
class ContainerEntry:
    role: Role
    container_name: str
    container_id: str
    status: ContainerStatus
    ip_addr: str

    def to_dict(self) -> dict[str, str]:
        return {
            "container_name": self.container_name,
            "container_id": self.container_id,
            "status": self.status,
            "role": self.role,
            "ip_addr": self.ip_addr,
        }

    @staticmethod
    def from_dict(obj: dict[str, str]) -> "ContainerEntry":
        return ContainerEntry(
            role=Role[obj["role"]],
            container_name=obj["container_name"],
            container_id=obj["container_id"],
            status=ContainerStatus[obj["status"]],
            ip_addr=obj["ip_addr"],
        )


class Status:
    @classmethod
    def get(cls) -> list[dict]:
        if not os.path.isfile(STATUS_FILE):
            with open(STATUS_FILE, "w") as file:
                json.dump([], file)

        with open(STATUS_FILE, "r") as file:
            return json.load(file)

    @classmethod
    def put(cls, status: list[dict]) -> None:
        with open(STATUS_FILE, "w") as file:
            json.dump(status, file)

    @classmethod
    def get_container_entry(cls, name: str) -> ContainerEntry:
        status = cls.get()

        for container_entry in status:
            if container_entry["container_name"] == name:
                return ContainerEntry.from_dict(container_entry)

        raise ContainerEntryNotFound

    @classmethod
    def add_container_entry(cls, container_entry: ContainerEntry) -> None:
        status = Status.get()

        status.append(container_entry.to_dict())

        Status.put(status)

    @classmethod
    def remove_container_entry(cls, container_entry: ContainerEntry) -> None:
        status = Status.get()

        status.remove(container_entry.to_dict())

        Status.put(status)

    @classmethod
    def get_used_ip_list(cls) -> set[str]:
        status = Status.get()

        return set([container_entry["ip_addr"] for container_entry in status])
