from __future__ import annotations

from dataclasses import dataclass
import re
import xml.etree.ElementTree as ET


BOUNDS_PATTERN = re.compile(
    r"^\[(-?\d+),(-?\d+)]\[(-?\d+),(-?\d+)]$"
)


@dataclass(frozen=True)
class Bounds:
    left: int
    top: int
    right: int
    bottom: int

    @classmethod
    def parse(cls, value: str) -> Bounds | None:
        match = BOUNDS_PATTERN.match(value)
        if not match:
            return None
        return cls(*(int(part) for part in match.groups()))

    @property
    def center(self) -> tuple[int, int]:
        return ((self.left + self.right) // 2, (self.top + self.bottom) // 2)

    def __str__(self) -> str:
        return f"[{self.left},{self.top}][{self.right},{self.bottom}]"


@dataclass(frozen=True)
class UiNode:
    text: str
    resource_id: str
    class_name: str
    content_description: str
    bounds: Bounds | None
    clickable: bool
    enabled: bool
    focusable: bool
    checked: bool | None

    @classmethod
    def from_element(cls, element: ET.Element) -> UiNode:
        checked_value = element.attrib.get("checked")
        checked = None if checked_value is None else checked_value == "true"
        return cls(
            text=element.attrib.get("text", "").strip(),
            resource_id=element.attrib.get("resource-id", "").strip(),
            class_name=element.attrib.get("class", "").strip(),
            content_description=element.attrib.get("content-desc", "").strip(),
            bounds=Bounds.parse(element.attrib.get("bounds", "")),
            clickable=element.attrib.get("clickable") == "true",
            enabled=element.attrib.get("enabled", "true") == "true",
            focusable=element.attrib.get("focusable") == "true",
            checked=checked,
        )

    @property
    def label(self) -> str:
        return self.text or self.content_description or self.resource_id or "(unlabeled)"

    def matches(self, query: str) -> bool:
        query = query.casefold()
        return any(
            query in value.casefold()
            for value in (self.text, self.resource_id, self.content_description)
        )

    def summary(self) -> str:
        flags = []
        if self.clickable:
            flags.append("clickable")
        if self.focusable:
            flags.append("focusable")
        if not self.enabled:
            flags.append("disabled")
        suffix = f" ({', '.join(flags)})" if flags else ""
        bounds = f" {self.bounds}" if self.bounds else ""
        return f"{self.label}{bounds}{suffix}"


class UiHierarchy:
    def __init__(self, nodes: tuple[UiNode, ...], raw_xml: str) -> None:
        self.nodes = nodes
        self.raw_xml = raw_xml

    @classmethod
    def parse(cls, xml: str) -> UiHierarchy:
        root = ET.fromstring(xml)
        nodes = tuple(UiNode.from_element(element) for element in root.iter("node"))
        return cls(nodes=nodes, raw_xml=xml)

    def find(self, query: str) -> list[UiNode]:
        return [node for node in self.nodes if node.matches(query)]

    def visible(self) -> list[UiNode]:
        return [
            node
            for node in self.nodes
            if node.text or node.content_description or node.resource_id
        ]

    def clickables(self) -> list[UiNode]:
        return [node for node in self.nodes if node.clickable and node.enabled]
