import importlib.resources
from importlib.metadata import version
from pathlib import Path
import time
from typing import List, Sequence, Tuple

import pandas as pd
import streamlit as st

from trendify.api.generator.data_product_collection import DataProductCollection
from trendify.api.plotting.plotting import PlotlyFigure

# from trendify.api.generator.data_product_collection import (
#     ProductIndexMap,
# )


def make_theme():
    theme_dir = Path(".streamlit").resolve()
    theme_dir.mkdir(parents=True, exist_ok=True)
    theme_dir.joinpath(".gitignore").write_text("*")

    toml = """[theme]
base="light"
primaryColor="#e92063"

[browser]
gatherUsageStats = false
"""
    theme_dir.joinpath("config.toml").write_text(toml)


def make_streamlit(trendify_dir: Path):
    trendify_dir = trendify_dir.resolve()
    save_location = trendify_dir.joinpath("assets", "dashboard", "streamlit_run.py")
    run_command = f"streamlit run {save_location.as_posix()}"
    to_write = f'''"""To run use:

{run_command}
"""

import trendify.streamlit as trendy_stream
from pathlib import Path

trendify_dir = Path("{trendify_dir.as_posix()}")

trendy_stream.make_dashboard(trendify_dir=trendify_dir)
'''
    make_theme()
    save_location.parent.mkdir(parents=True, exist_ok=True)
    save_location.write_text(to_write)
    print(
        f"""To run use

{run_command}
"""
    )


def get_index_map_path(trendify_dir: Path, tag: Tuple[str, ...]) -> Path:
    products_dir = trendify_dir.joinpath("products")
    return products_dir.joinpath(*tag, "index_map")


def get_tags(trendify_dir: Path) -> Sequence[Tuple[str, ...]]:
    products_dir = trendify_dir.joinpath("products")
    tags = [
        p.parent.relative_to(products_dir).parts
        for p in products_dir.rglob("*")
        if p.name == "index_map" and p.is_file()
    ]
    return sorted(tags, key=lambda x: (len(x), x))


def create_nested_expanders(
    tags: Sequence[Tuple[str, ...]], current_level: int = 0
) -> dict:
    # Group tags by their current level
    level_groups = {}
    for tag in tags:
        if len(tag) > current_level:
            if tag[current_level] not in level_groups:
                level_groups[tag[current_level]] = {
                    "subtags": [],  # Tags that continue deeper
                    "complete": False,  # Whether this level is a complete tag
                }
            if len(tag) == current_level + 1:
                level_groups[tag[current_level]]["complete"] = True
            else:
                level_groups[tag[current_level]]["subtags"].append(tag)

    return level_groups


def render_nested_expanders(
    tags: Sequence[Tuple[str, ...]],
    current_level: int = 0,
    selected_tags: Tuple[str, ...] | None = None,
):
    if selected_tags is None:
        selected_tags = None

    level_groups = create_nested_expanders(tags, current_level)

    # Get currently selected tag (if any)
    selected_tag = st.session_state.get("selected_tags", None)

    for tag_name, group_info in level_groups.items():
        # Create the full tag tuple up to this level
        current_tag = tuple(
            t[: current_level + 1]
            for t in tags
            if len(t) > current_level and t[current_level] == tag_name
        )
        if current_tag:
            # Take the first one since they're all the same at this level
            current_tag = current_tag[0]

        # Check if this tag is part of the currently selected path
        is_selected = selected_tag == current_tag
        button_text = f"{tag_name}"
        button_type = "primary" if is_selected else "secondary"

        # Only create expander if there are subtags, otherwise just show button
        if group_info["subtags"]:
            with st.expander(f"📁 {tag_name}", expanded=False):
                if group_info["complete"]:
                    if st.button(
                        button_text,
                        key=f"btn_{str('_').join(current_tag)}",  # Use the full tag tuple as the key
                        type=button_type,
                    ):
                        st.session_state.selected_tags = current_tag
                        st.rerun()

                render_nested_expanders(
                    group_info["subtags"], current_level + 1, selected_tags
                )
        else:
            # For leaf nodes (no subtags), just show the button
            if group_info["complete"]:
                if st.button(
                    button_text,
                    key=f"btn_{str('_').join(current_tag)}",  # Use the full tag tuple as the key
                    type=button_type,
                    use_container_width=True,
                ):
                    st.session_state.selected_tags = current_tag
                    st.rerun()

    return st.session_state.get("selected_tags", None)


def make_sidebar(trendify_dir: Path) -> Tuple[str, ...] | None:
    st.title(f"Trendify (v{version("trendify")})")

    tags = get_tags(trendify_dir=trendify_dir)
    st.caption(f"Viewing {len(tags)} assets for {trendify_dir}")

    if "selected_tags" not in st.session_state:
        st.session_state.selected_tags = None

    selected_tags = st.session_state.selected_tags
    selected_tags = render_nested_expanders(tags=tags, selected_tags=selected_tags)

    return selected_tags


@st.cache_data(show_time=True)
def process_tag(tag: Tuple[str, ...], trendify_dir: Path):
    products_paths = list(
        trendify_dir.joinpath("products").joinpath(*tag).glob("*.json")
    )

    return DataProductCollection.process_tag_for_streamlit(products_paths, tag=tag)


def make_main_page(tag: Tuple[str, ...], trendify_dir: Path):
    """Display the main page content for the selected tag"""

    st.title(f"{" | ".join(tag)}")

    # Process the tag for tables and plots
    proccessed_tag = process_tag(tag=tag, trendify_dir=trendify_dir)

    # Display Plotly figures if available
    if isinstance(proccessed_tag, PlotlyFigure):
        col1, col2, col3 = st.columns([1, 1, 0.3], vertical_alignment="bottom")
        with st.form("plot_form"):
            with col1:
                if "height" not in st.session_state:
                    st.session_state.height = 600

                height = st.slider(
                    label="Figure Height",
                    min_value=100,
                    value=st.session_state.height,
                    max_value=2000,
                    step=100,
                    help="Set the height of the rendered plot (in pixels)",
                )
            with col2:
                opts = ["closest", "x unified", "y unified", "x", "y"]
                if "tooltip_selected" not in st.session_state:
                    st.session_state.tooltip_selected = "closest"

                index = opts.index(st.session_state.tooltip_selected)

                tooltip = st.selectbox(
                    key="tooltip",
                    label="Tooltip",
                    options=opts,
                    index=index,
                    accept_new_options=False,
                    help="Select tooltip option",
                )

            with col3:
                if st.button(
                    "🔄",
                    key="refresh_button",
                    help="Refresh the plot area with the selections made.",
                ):
                    st.session_state.height = height
                    st.session_state.tooltip_selected = tooltip
                    st.rerun()

        proccessed_tag.fig.update_layout(
            hovermode=st.session_state.tooltip_selected,
            height=st.session_state.height,
            margin=dict(pad=4, t=25, b=25),
        )
        st.plotly_chart(proccessed_tag.fig)

    else:
        msg = f"Product with {tag=} does not have a display method for streamlit"
        st.warning(msg)


def make_dashboard(trendify_dir: str | Path):
    start = time.perf_counter()

    trendify_dir = Path(trendify_dir).resolve()

    with importlib.resources.path("trendify.assets", "logo.svg") as data_path:
        logo = data_path

    with importlib.resources.path("trendify.assets", "logo_white_bg.svg") as data_path:
        logo_white_bg = data_path

    docs = "https://talbotknighton.github.io/trendify/"

    st.set_page_config(
        page_title="Trendify UI",
        page_icon=logo_white_bg,
        layout="wide",
        menu_items={
            "Get help": docs,
            "Report a bug": "https://github.com/TalbotKnighton/trendify/issues",
            "About": "Trendify",
        },
    )

    st.markdown(
        """
    <style>
    .stAppDeployButton {
        display: none;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.logo(
        image=f"{logo}",
        size="large",
        link=docs,
    )

    with st.sidebar:
        selected_tag = make_sidebar(trendify_dir=trendify_dir)

    if selected_tag is None:
        st.info("Select an Asset to Display")
    else:
        make_main_page(tag=selected_tag, trendify_dir=trendify_dir)

    with st.sidebar:
        st.caption(f"Site built in {time.perf_counter()-start:.2f} seconds")


def main():
    """To run use

    streamlit run src/trendify/streamlit.py
    """
    make_theme()
    make_dashboard(trendify_dir=Path("sample_data/trendify"))


if __name__ == "__main__":
    main()
