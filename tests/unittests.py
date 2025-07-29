import unittest
import numpy as np
from pathlib import Path
import tempfile
import json
import matplotlib.pyplot as plt
from trendify import (
    Trace2D,
    Point2D,
    TableEntry,
    HistogramEntry,
    AxLine,
    Pen,
    Marker,
    Format2D,
    LineOrientation,
    DataProductCollection,
)


class TestDataProducts(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

    def test_trace2d(self):
        # Test creating and manipulating a Trace2D
        x = np.linspace(0, 10, 100)
        y = np.sin(x)

        trace = Trace2D.from_xy(
            tags=["test_trace"],
            x=x,
            y=y,
            pen=Pen(color="blue", label="Test Sine"),
            format2d=Format2D(title_fig="Test Figure", label_x="X", label_y="Y"),
        )

        # Test properties
        np.testing.assert_array_equal(trace.x, x)
        np.testing.assert_array_equal(trace.y, y)
        self.assertEqual(trace.pen.color, "blue")
        self.assertEqual(trace.pen.label, "Test Sine")

        # Test plotting
        fig, ax = plt.subplots()
        trace.plot_to_ax(ax)
        plt.close(fig)

    def test_point2d(self):
        point = Point2D(
            tags=["test_point"],
            x=1.0,
            y=2.0,
            marker=Marker(color="red", symbol="o"),
            format2d=Format2D(title_fig="Test Point"),
        )

        self.assertEqual(point.x, 1.0)
        self.assertEqual(point.y, 2.0)
        self.assertEqual(point.marker.color, "red")

    def test_axline(self):
        # Test horizontal line
        hline = AxLine(
            tags=["test_line"],
            value=5.0,
            orientation=LineOrientation.HORIZONTAL,
            pen=Pen(color="red", label="Test HLine"),
        )

        self.assertEqual(hline.value, 5.0)
        self.assertEqual(hline.orientation, LineOrientation.HORIZONTAL)

        # Test vertical line
        vline = AxLine(
            tags=["test_line"],
            value=2.0,
            orientation=LineOrientation.VERTICAL,
            pen=Pen(color="blue", label="Test VLine"),
        )

        self.assertEqual(vline.value, 2.0)
        self.assertEqual(vline.orientation, LineOrientation.VERTICAL)

        # Test plotting
        fig, ax = plt.subplots()
        hline.plot_to_ax(ax)
        vline.plot_to_ax(ax)
        plt.close(fig)

    def test_table_entry(self):
        entry = TableEntry(
            tags=["test_table"],
            row="Test Row",
            col="Test Col",
            value=42.0,
            unit="units",
        )

        self.assertEqual(entry.row, "Test Row")
        self.assertEqual(entry.col, "Test Col")
        self.assertEqual(entry.value, 42.0)
        self.assertEqual(entry.unit, "units")

    def test_histogram_entry(self):
        entry = HistogramEntry(tags=["test_hist"], value=3.14, style=None)

        self.assertEqual(entry.value, 3.14)

    def test_data_product_collection(self):
        # Create some test products
        point = Point2D(tags=["test"], x=1.0, y=2.0, marker=Marker(color="red"))

        trace = Trace2D.from_xy(
            tags=["test"],
            x=np.array([1, 2, 3]),
            y=np.array([4, 5, 6]),
            pen=Pen(color="blue"),
        )

        # Create collection
        collection = DataProductCollection(elements=[point, trace])

        # Test serialization
        json_file = self.test_dir / "test.json"
        json_file.write_text(collection.model_dump_json())

        # Test deserialization
        loaded = DataProductCollection.model_validate_json(json_file.read_text())

        self.assertEqual(len(loaded.elements), 2)
        self.assertIsInstance(loaded.elements[0], Point2D)
        self.assertIsInstance(loaded.elements[1], Trace2D)


if __name__ == "__main__":
    unittest.main()
