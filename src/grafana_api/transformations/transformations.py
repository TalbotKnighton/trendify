"""
```json
{
    "id": "merge",
    "options": {}
},
{
    "id": "partitionByValues",
    "options": {
        "fields": [
            "label"
        ],
        "keepFields": false,
        "naming": {
            "asLabels": false
        }
    }
}
```
"""
from typing import Any
from pydantic import BaseModel

class Transformation(BaseModel):
    """
    
    """
    id: str

class Merge(Transformation):
    id: str = 'merge'
    options: dict = {}

class PartitionByValues(Transformation):

    id: str = 'partitionByValues'
    options: dict[str, Any]

    @classmethod
    def from_fields(
            cls, 
            fields: list[str], 
            keep_fields: bool = False,
            fields_as_labels: bool = False,
        ):
        return cls(
            options={
                "fields": fields,
                "keepFields": keep_fields,
                "naming": {
                    "asLabels": fields_as_labels
                }
            }
        )