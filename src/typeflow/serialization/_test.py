from pathlib import Path
from typing import ClassVar, List, Optional

from typeflow.serialization import (
    SerializableModel,
    NamedModel,
    SerializableCollection,
    NamedCollection,
)


# Example models
class Point(SerializableModel):
    """A simple point model."""

    version: ClassVar[str] = "1.0.0"

    x: float
    y: float

    def distance_from_origin(self) -> float:
        return (self.x**2 + self.y**2) ** 0.5


class ColoredPoint(Point):
    """A point with a color."""

    version: ClassVar[str] = "1.0.0"

    color: str = "black"


class Shape(NamedModel):
    """A named shape with points."""

    version: ClassVar[str] = "1.0.0"

    points: List[Point] = []
    color: Optional[str] = None


def example_usage():
    # Create some models
    p1 = Point(x=1.0, y=2.0)
    p2 = Point(x=3.0, y=4.0)
    cp1 = ColoredPoint(x=5.0, y=6.0, color="red")

    # Using SerializableCollection
    points = SerializableCollection[Point]()
    points.append(p1)
    points.append(p2)
    points.append(cp1)  # ColoredPoint is a subclass of Point

    print(f"Collection has {len(points)} points")
    print(f"First point: ({points[0].x}, {points[0].y})")

    # Find points with specific properties
    far_points = points.filter(lambda p: p.distance_from_origin() > 5.0)
    print(f"Found {len(far_points)} points far from origin")

    # Group by type
    grouped = points.group_by_type()
    for type_name, type_points in grouped.items():
        print(f"{len(type_points)} instances of {type_name}")

    # Using NamedCollection
    shapes = NamedCollection[Shape]()

    # Create and add shapes
    triangle = Shape(
        name="triangle",
        points=[Point(x=0.0, y=0.0), Point(x=1.0, y=0.0), Point(x=0.5, y=0.866)],
        color="blue",
    )

    square = Shape(
        name="square",
        points=[
            Point(x=0.0, y=0.0),
            Point(x=1.0, y=0.0),
            Point(x=1.0, y=1.0),
            Point(x=0.0, y=1.0),
        ],
        color="green",
    )

    shapes.add(triangle)
    shapes.add(square)

    print(f"\nShapes collection has {len(shapes)} shapes")
    print(f"Shape names: {', '.join(shapes.keys())}")

    # Access by name
    print(f"Triangle has {len(shapes['triangle'].points)} points")

    # Filter by property
    blue_shapes = shapes.filter(lambda s: s.color == "blue")
    print(f"Found {len(blue_shapes)} blue shapes")

    # Save to file
    output_dir = Path("./output")
    output_dir.mkdir(exist_ok=True)

    shapes.save_to_file(output_dir / "shapes.json")
    points.save_to_file(output_dir / "points.json")

    # Load from file
    loaded_shapes = NamedCollection.from_file(output_dir / "shapes.json")
    loaded_points = SerializableCollection.from_file(output_dir / "points.json")

    print(f"\nLoaded {len(loaded_shapes)} shapes and {len(loaded_points)} points")

    # Convert between collection types
    shapes_list = loaded_shapes.to_serializable_collection()
    print(f"Converted to list collection with {len(shapes_list)} items")
    print(shapes.model_dump_json(indent=4))


if __name__ == "__main__":
    example_usage()
