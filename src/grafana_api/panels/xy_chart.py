"""
Need to produce a Dashboard
```
"""
# Standard Imports
from typing import Dict, List
# Common Imports
from pydantic import BaseModel
# Local Imports
from grafana_api.transformations.transformations import Transformation

__all__ = [
    'DataSource',
    'DefaultDataSource',
    'Color',
    'HideFrom',
    'LineStyle',
    'PointSize',
    'ScaleDistribution',
    'Custom',
    'Threshold',
    'Thresholds',
    'Defaults',
    'FieldConfig',
    'GridPosition',
    'Legend',
    'Matcher',
    'Series',
    'ToolTip',
    'Options',
    'URLOptions',
    'Target',
    'Panel',
]

class DataSource(BaseModel):
    """
    """
    type: str = 'yesoreyeram-infinity-datasource'
    uid: str = 'be1d76jvnf668b'
class DefaultDataSource(DataSource):
    """
    """
    default: bool = True
class Color(BaseModel):
    fixedColor: str = "semi-dark-blue"
    mote: str = "palette-classic"
class HideFrom(BaseModel):
    """
    {
        "legend": false,
        "tooltip": false,
        "viz": false
    }
    """
    legend: bool = False
    tooltip: bool = False
    viz: bool = False
class LineStyle(BaseModel):
    """
    ```json
    {
        "fill": "solid"
    }
    ```
    """
    fill: str = 'solid'
class PointSize(BaseModel):
    """
    ```json
    {
        "fixed": 3
    }
    ```
    """
    fixed: int = 3
class ScaleDistribution(BaseModel):
    """
    ```json
    {
        "type": "linear"
    }
    ```
    """
    type: str = 'linear'
class Custom(BaseModel):
    axisBorderShow: bool = False
    axisCenteredZero: bool = False
    axisColorMode: str = "text"
    axisLabel: str = ""
    axisPlacement: str = "auto"
    fillOpacity: int = 50
    hideFrom: HideFrom = HideFrom()
    lineStyle: LineStyle = LineStyle()
    lineWidth: int = 2
    pointShape: str = "circle"
    pointSize: PointSize = PointSize()
    pointStrokeWidth: int = 1
    scaleDistribution: ScaleDistribution = ScaleDistribution()
    show: str = "points"  # points, lines, both (I think)
class Threshold(BaseModel):
    """
    ```json
    {
        "color": "green",
        "value": null
    }
    ```
    """
    color: str = 'green'
    value: float | None = None
class Thresholds(BaseModel):
    """
    ```json
    "thresholds": {
        "mode": "absolute",
        "steps": [
            
        ]
    }
    ```
    """
    mode: str = 'absolute'
    steps: list[Threshold] = [Threshold()]
class Defaults(BaseModel):
    color: Color = Color()
    cusom: Custom = Custom()
    fieldMinMax: bool = False
    mappings: list = []
    thresholds: Thresholds = Thresholds()
class FieldConfig(BaseModel):
    """
    ```json
     "fieldConfig": {
        "defaults": {
            
            "fieldMinMax": false,
            "mappings": [],
            
        },
        "overrides": []
    },
    ```
    """
    defaults: Defaults = Defaults()
    overrides: list = []
class GridPosition(BaseModel):
    """
    ```json
    "gridPos": {
        "h": 8,
        "w": 12,
        "x": 12,
        "y": 16
    }
    ```
    """
    h: int = 16
    w: int = 24
    x: int = 0
    y: int = 0
class Legend(BaseModel):
    """
    """
    calcs: list = []
    displayMode: str = 'list'  # 'list' or 'table'
    placement: str = 'bottom'
    showLegend: bool = True
    sortBy: str = 'Name'
    sortDesc: bool = False
class MatcherOptions(BaseModel):
    """
    """
    options: str  # x or y
    id: str = 'byName'
class Matcher(BaseModel):
    matcher: MatcherOptions
class Series(BaseModel):
    """
    """
    x: Matcher = Matcher(matcher=MatcherOptions(options='x'))
    y: Matcher = Matcher(matcher=MatcherOptions(options='y'))
class ToolTip(BaseModel):
    """
    """
    mode: str = 'single'
    sort: str = 'none'
class Options(BaseModel):
    """
    """
    legend: Legend = Legend()
    mapping: str = 'auto'
    series: list[Series] = [Series()]
    tooltop: ToolTip = ToolTip()
class URLOptions(BaseModel):
    """
    """
    data: str = ''
    method: str = 'GET'
class Target(BaseModel):
    """
    """
    columns: list = []
    datasource: DataSource = DataSource()
    filters: list = []
    format: str = 'table'
    global_query_id: str = ''
    hide: bool = False
    parser: str = 'uql'
    refId: str = 'A'  # Table name
    root_selector: str = ''
    source: str = 'url'
    type: str = 'json'
    uql: str = "parse-json\n| project \"elements\"\n| extend \"label\"=\"pen.label\"\n| extend \"label1\"=substring(\"label\",0,2)\n| extend \"label2\"=substring(\"label\",3)\n| mv-expand \"points\"\n| extend \"x\"=\"points.x\", \"y\"=\"points.y\"\n#| project \"label1\", \"label2\", \"x\", \"y\", \"color\"=mul(\"label2\", 0.1)\n#| project \"label1\", \"x\", \"y\"\n| project \"label\", \"x\", \"y\", \"metadata\"\n\n\n"
    url: str # = "http://localhost:8000/data_products/workdir.products/trace_plots/Trace2D"
    url_options: URLOptions = URLOptions()
class Panel(BaseModel):
    """
    """
    datasource: DataSource = DefaultDataSource()
    fieldConfig: FieldConfig = FieldConfig()
    gridPos: GridPosition = GridPosition()
    id: int = 1
    options: Options = Options()
    pluginVersion: str = '11.2.2'
    targets: list[Target]# = [Target()]
    title: str = "Example XY Chart for Trace2D Data"
    transformations: list[Transformation] = []
    type: str = 'xychart'