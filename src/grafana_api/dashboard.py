"""
Dashboard definition
"""

# Standard imports
from typing import List, Dict
# Common imports
from pydantic import BaseModel
# Local imports
from grafana_api.panels.xy_chart import Panel
__all__ = [
    'Annotation',
    'Annotations',
    'Dashboard',
]
class Annotation(BaseModel):
    """
    """
    builtIn: int = 1
    datasource: dict = {"type": "grafana", "uid": "-- Grafana --"}
    enable: bool = True
    hide: bool = True
    iconColor: str = 'rgba(0, 211, 255, 1)'
    name: str = 'Annotation & Alers'
    type: str = 'dashboard'
class Annotations(BaseModel):
    """
    """
    list: List[Annotation] = [Annotation()]
class Dashboard(BaseModel):
    """
    """
    annotations: Annotations = Annotations()
    description: str = "Try Parsing JSON Data"
    editable: bool = True
    fiscalYearStartMonth: int = 0
    graphTooltip: int = 0
    id: int = 1
    links: list = []
    panels: list[Panel]# = [Panel()]
    refresh: str = ""
    schemaVersion: int = 39
    tags: list = []
    templating: Dict = {'list': []}
    time: Dict = {'from': 'now-6h', 'to': 'now'}
    timepicker: Dict = {}
    timezone: str = 'browser'
    title: str = 'DemoDashboard'
    uid: str = 'de1dapkdr47wgf'
    version: int = 20
    weekStart: str = ''


if __name__ == '__main__':
    print(Dashboard().model_dump_json(indent=4))