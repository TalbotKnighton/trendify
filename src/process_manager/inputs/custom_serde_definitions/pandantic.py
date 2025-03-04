
"""
Defines types for Pandas Series and DataFrame serialization and deserialization.
"""
from __future__ import annotations

# Standard
from typing import Any, Annotated

# External
import numpy as np
from numpydantic import NDArray, Shape  
import pandas as pd
from pydantic import BaseModel, BeforeValidator, WrapSerializer, FieldSerializationInfo, SerializerFunctionWrapHandler

__all__ = [
    "SeriesSerDe",
    "DataFrameSerDe",
    "PandasSeries",
    "PandasDataFrame",
]

def np_encoder(object):
    """
    JSON encoder function for numpy types.

    Args:
        object (Any): Object to encode

    Returns:
        Any: Encoded object
    """
    if isinstance(object, np.generic):
        return object.item()
    else:
        return object

class SeriesSerDe(BaseModel):
    """
    Class to serialize and deserialize Pandas Series objects.
    
    Attributes:
        name (int|str|None): Name of the series
        values (NDArray[Shape["*"], Any]): Values of the series
        index (NDArray[Shape["*"], Any]): Index of the series
        index_name (int|str|None): Name of the index
    Methods:
        as_series(): Convert to Pandas Series object
        from_dict(data: dict) -> SeriesSerDe: Create a new instance from a dictionary
        model_validate_json(json: str | bytes, loc: Any = None, prop: Any = None, cls: Any = None, **kwargs: Any) -> Self: Validate and deserialize JSON data into the model.
    """
    # Attributes
    name: int | str | None
    values: NDArray[Shape["*"], Any]
    index: NDArray[Shape["*"], Any]
    index_name: int | str | None

    def as_series(self):
        """
        Convert to Pandas Series object.

        Returns:
            (pd.Series): Pandas Series object from stored data
        """
        return pd.Series(self.values, name=self.name, index=pd.Index(self.index, name=self.index_name))

    @classmethod
    def to_series(cls, input: pd.Series | dict | str):
        """
        Convert input to a Pandas Series object.

        Args:
            input (pd.Series | dict | str): Input data to convert.

        Returns:
            (pd.Series): Pandas Series object from input data.
        """
        if isinstance(input, str):
            print('str')
            return cls.model_validate_json(input).as_series()
        elif isinstance(input, dict):
            print('dict')
            return cls.from_dict(input)
        elif isinstance(input, pd.Series):
            print('series')
            return input
        else:
            raise ValueError(input)
    
    @classmethod
    def from_dict(cls, d: dict):
        """
        Create a new instance from a dictionary.

        Args:
            d (dict): Dictionary containing the data.
        
        Returns:
            (cls): New instance created from the dictionary.
        """
        try:
            return pd.Series(
                d['values'], 
                name=d['name'],
                index=pd.Index(
                    d['index'], 
                    name=d['index_name'],
                ),
            )
        except:
            raise ValueError(d)
    
    @classmethod
    def from_series(cls, series: pd.Series, nxt: SerializerFunctionWrapHandler, info: FieldSerializationInfo):
        """
        Create a new instance from a Pandas Series object.

        Args:
            series (pd.Series): Pandas Series object to convert.
        
        Returns:
            (cls): New instance created from the Pandas Series object.
        """
        return cls(
            name=series.name,
            values=series.values,
            index=series.index.values,
            index_name=series.index.name,
        )
    
PandasSeries = Annotated[
    pd.Series,
    # deserialization
    BeforeValidator(SeriesSerDe.to_series),
    # serialization
    WrapSerializer(SeriesSerDe.from_series),
]
"""
Type alias for Pandas Series objects that can be serialized and deserialized.
This type alias is used to define the expected data structure when working with Pandas Series objects in a way that allows them to be both serialized and deserialized using the `SeriesSerDe` class.
The `PandasSeries` type alias is defined as an Annotated type, which means it has two type arguments: `pd.Series`, which specifies the expected data structure for this type, and a BeforeValidator and PlainSerializer, respectively.
This allows you to use Pandas Series objects in your code while ensuring that they can be serialized and deserialized using the `SeriesSerDe` class.
"""


class DataFrameSerDe(BaseModel):
    """
    Class to serialize and deserialize Pandas DataFrame objects.
    
    Attributes:
        columns (NDArray[Shape["*"], Any]): Column names of the dataframe
        values (NDArray[Shape["*, *"], Any]): Values of the dataframe
        index (NDArray[Shape["*"], Any]): Index of the dataframe
        index_name (int|str|None): Name of the index
        column_names (list[int|str|None]): Names of the columns
    Methods:
        as_dataframe(): Convert to Pandas DataFrame object
        from_dict(data: dict) -> DataFrameSerDe: Create a new instance from a dictionary
        model_validate_json(json: str | bytes, loc: Any = None, prop: Any = None, cls: Any = None, **kwargs: Any) -> Self: Validate and deserialize JSON data into the model.
    """
    # Attributes
    columns: NDArray[Shape["*"], Any]
    values: NDArray[Shape["*, *"], Any]
    index: NDArray[Shape["*"], Any]
    index_name: int | str | None
    column_names: list[int | str | None] | None

    def as_dataframe(self):
        """
        Convert to Pandas DataFrame object.

        Returns:
            (pd.DataFrame): Pandas DataFrame object from stored data
        """
        return pd.DataFrame(
            self.values, 
            columns=pd.Index(self.columns, name=self.column_names), 
            index=pd.Index(self.index, name=self.index_name)
        )

    @classmethod
    def to_dataframe(cls, input: pd.DataFrame | dict | str):
        """
        Convert input to a Pandas DataFrame object.

        Args:
            input (pd.DataFrame | dict | str): Input data to convert.

        Returns:
            (pd.DataFrame): Pandas DataFrame object from input data.
        """
        if isinstance(input, str):
            return cls.model_validate_json(input).as_dataframe()
        elif isinstance(input, dict):
            return cls.from_dict(input)
        elif isinstance(input, pd.DataFrame):
            return input
        else:
            # breakpoint()
            raise ValueError(input)
    
    @classmethod
    def from_dict(cls, d: dict):
        """
        Create a new instance from a dictionary.

        Args:
            d (dict): Dictionary containing the data.
        
        Returns:
            (pd.DataFrame): New DataFrame created from the dictionary.
        """
        try:
            return pd.DataFrame(
                d['values'],
                columns=pd.Index(d['columns'], name=d['column_names']),
                index=pd.Index(d['index'], name=d['index_name'])
            )
        except:
            raise ValueError(d)
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, nxt: SerializerFunctionWrapHandler, info: FieldSerializationInfo):
        """
        Create a new instance from a Pandas DataFrame object.

        Args:
            df (pd.DataFrame): Pandas DataFrame object to convert.
        
        Returns:
            (cls): New instance created from the Pandas DataFrame object.
        """
        return cls(
            columns=df.columns.values,
            values=df.values,
            index=df.index.values,
            index_name=df.index.name,
            column_names=df.columns.name
        )

PandasDataFrame = Annotated[
    pd.DataFrame,
    # deserialization
    BeforeValidator(DataFrameSerDe.to_dataframe),
    # serialization  
    WrapSerializer(DataFrameSerDe.from_dataframe),
]
"""
Type alias for Pandas DataFrame objects that can be serialized and deserialized.
This type alias is used to define the expected data structure when working with Pandas DataFrame objects in a way that allows them to be both serialized and deserialized using the `DataFrameSerDe` class.
The `PandasDataFrame` type alias is defined as an Annotated type, which means it has two type arguments: `pd.DataFrame`, which specifies the expected data structure for this type, and a BeforeValidator and PlainSerializer, respectively.
This allows you to use Pandas DataFrame objects in your code while ensuring that they can be serialized and deserialized using the `DataFrameSerDe` class.
"""