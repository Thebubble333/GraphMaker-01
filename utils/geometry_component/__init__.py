import streamlit.components.v1 as components
import os

_component_func = components.declare_component(
    "geometry_editor",
    path=os.path.dirname(os.path.abspath(__file__))
)

def geometry_editor(shapes, width, height, show_grid=False, key=None):
    """
    Renders the Geometry Editor component.
    """
    return _component_func(
        shapes=shapes,
        width=width,
        height=height,
        show_grid=show_grid,
        key=key,
        default=None
    )