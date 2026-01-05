"""
Utilities to open KMZ/KML files and extract polygon coordinates.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from pathlib import Path
from typing import Dict, List, Tuple
import zipfile
from xml.etree import ElementTree as ET


@dataclass
class FieldGeometry:
    """Simple representation of a talhao polygon."""

    name: str
    coordinates: List[Tuple[float, float]]  # (lat, lon)
    source: Path
    area_ha: float = 0.0
    municipality: str | None = None
    cultivation: str | None = None
    metadata: Dict[str, str] = field(default_factory=dict)


class KMZLoader:
    """Load talhao geometries from KMZ or KML files."""

    DEFAULT_NS = {"kml": "http://www.opengis.net/kml/2.2"}

    @staticmethod
    def load_fields(path: str | Path) -> List[FieldGeometry]:
        """Return every polygon stored in the provided KMZ/KML file."""
        filepath = Path(path).expanduser().resolve()
        data = KMZLoader._read_raw_kml(filepath)
        return KMZLoader._parse_kml(data, filepath)

    @staticmethod
    def _read_raw_kml(filepath: Path) -> str:
        suffix = filepath.suffix.lower()
        if suffix == ".kmz":
            with zipfile.ZipFile(filepath) as archive:
                kml_name = KMZLoader._locate_kml(archive)
                if not kml_name:
                    raise ValueError("Arquivo KMZ sem arquivo .kml interno.")
                return archive.read(kml_name).decode("utf-8")
        if suffix == ".kml":
            return filepath.read_text(encoding="utf-8")
        raise ValueError(f"Extensao nao suportada: {filepath.suffix}")

    @staticmethod
    def _locate_kml(archive: zipfile.ZipFile) -> str | None:
        for name in archive.namelist():
            if name.lower().endswith(".kml"):
                return name
        return None

    @staticmethod
    def _parse_kml(kml_string: str, source: Path) -> List[FieldGeometry]:
        root = ET.fromstring(kml_string)
        ns = KMZLoader._discover_namespace(root)
        fields: List[FieldGeometry] = []
        for placemark in root.findall(".//kml:Placemark", ns):
            name_element = placemark.find("kml:name", ns)
            base_name = (
                name_element.text.strip()
                if name_element is not None and name_element.text
                else source.stem
            )
            polygons = KMZLoader._extract_polygons(placemark, ns)
            for index, polygon in enumerate(polygons, start=1):
                tag_name = base_name if len(polygons) == 1 else f"{base_name} #{index}"
                area = KMZLoader._estimate_area_hectares(polygon)
                fields.append(
                    FieldGeometry(
                        name=tag_name,
                        coordinates=polygon,
                        source=source,
                        area_ha=area,
                        municipality=None,
                    )
                )
        return fields

    @staticmethod
    def _discover_namespace(root: ET.Element) -> dict:
        if root.tag.startswith("{"):
            uri = root.tag.split("}")[0].strip("{")
            return {"kml": uri}
        return KMZLoader.DEFAULT_NS

    @staticmethod
    def _extract_polygons(
        placemark: ET.Element, ns: dict
    ) -> List[List[Tuple[float, float]]]:
        polygons: List[List[Tuple[float, float]]] = []
        for polygon in placemark.findall(".//kml:Polygon", ns):
            coords = polygon.find(".//kml:coordinates", ns)
            if coords is None or not coords.text:
                continue
            parsed = KMZLoader._parse_coordinate_string(coords.text)
            if parsed:
                polygons.append(parsed)
        return polygons

    @staticmethod
    def _parse_coordinate_string(data: str) -> List[Tuple[float, float]]:
        points: List[Tuple[float, float]] = []
        chunks = (chunk.strip() for chunk in data.strip().split())
        for chunk in chunks:
            if not chunk:
                continue
            pieces = chunk.split(",")
            if len(pieces) < 2:
                continue
            lon, lat = float(pieces[0]), float(pieces[1])
            points.append((lat, lon))
        return points

    @staticmethod
    def _estimate_area_hectares(coords: List[Tuple[float, float]]) -> float:
        if len(coords) < 3:
            return 0.0
        # Simple equirectangular projection before shoelace formula
        avg_lat = sum(lat for lat, _ in coords) / len(coords)
        rad_lat = math.radians(avg_lat)
        radius = 6378137.0  # meters
        cos_lat = math.cos(rad_lat)
        projected = []
        for lat, lon in coords:
            x = math.radians(lon) * radius * cos_lat
            y = math.radians(lat) * radius
            projected.append((x, y))
        area = 0.0
        for i in range(len(projected)):
            x1, y1 = projected[i]
            x2, y2 = projected[(i + 1) % len(projected)]
            area += x1 * y2 - x2 * y1
        return abs(area) / 2 / 10000  # square meters to hectares
