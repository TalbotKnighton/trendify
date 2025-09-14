import importlib.resources
from importlib.metadata import version
from pathlib import Path
import time
from typing import List, Sequence, Tuple

import streamlit as st

from trendify.api.base.helpers import DATA_PRODUCTS_FNAME_DEFAULT, Tag, Tags
from trendify.api.generator.data_product_collection import DataProductCollection


def make_theme():
    theme_dir = Path(".streamlit").resolve()
    theme_dir.mkdir(parents=True, exist_ok=True)
    theme_dir.joinpath(".gitignore").write_text("*")

    toml = """[theme]
base="dark"
primaryColor="#e92063"
"""
    theme_dir.joinpath("config.toml").write_text(toml)


def get_tags(workdir: Path) -> Sequence[Tuple[str, ...]]:
    products_dir = workdir.joinpath("products")
    return [
        p.parent.relative_to(products_dir).parts
        for p in products_dir.rglob("*")
        if p.name == "index_map" and p.is_file()
    ]


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
            t[current_level]
            for t in tags
            if len(t) > current_level and t[current_level] == tag_name
        )
        if current_tag:
            current_tag = current_tag[
                :1
            ]  # Take just the first one since they're all the same at this level

        # Check if this tag is part of the currently selected path
        is_selected = (
            selected_tag is not None
            and len(selected_tag) > current_level
            and selected_tag[current_level] == tag_name
        )
        button_text = f"{tag_name}"
        button_type = "primary" if is_selected else "secondary"

        # Only create expander if there are subtags, otherwise just show button
        if group_info["subtags"]:
            with st.expander(f"📁 {tag_name}", expanded=True):
                if group_info["complete"]:
                    if st.button(
                        button_text,
                        key=f"btn_{current_level}_{tag_name}",
                        type=button_type,
                    ):
                        # Find the complete tag tuple for this selection
                        full_tag = next(
                            (
                                t
                                for t in tags
                                if len(t) == current_level + 1
                                and t[current_level] == tag_name
                            ),
                            None,
                        )
                        st.session_state.selected_tags = full_tag
                        st.rerun()

                render_nested_expanders(
                    group_info["subtags"], current_level + 1, selected_tags
                )
        else:
            # For leaf nodes (no subtags), just show the button
            if group_info["complete"]:
                if st.button(
                    button_text,
                    key=f"btn_{current_level}_{tag_name}",
                    type=button_type,
                    use_container_width=True,
                ):
                    # Find the complete tag tuple for this selection
                    full_tag = next(
                        (
                            t
                            for t in tags
                            if len(t) == current_level + 1
                            and t[current_level] == tag_name
                        ),
                        None,
                    )
                    st.session_state.selected_tags = full_tag
                    st.rerun()

    return st.session_state.get("selected_tags", None)


def make_sidebar(workdir: Path):
    st.title(f"Trendify (v{version("trendify")})")
    st.caption(f"Viewing assets for {workdir}")

    products_dir = workdir.joinpath("products")
    product_dirs = list(products_dir.glob("**/*/"))

    tags = get_tags(workdir=workdir)

    st.caption(f"Located {len(tags)} assets")

    if "selected_tags" not in st.session_state:
        st.session_state.selected_tags = None

    selected_tags = st.session_state.selected_tags
    st.info("Select an Asset")
    selected_tags = render_nested_expanders(tags=tags, selected_tags=selected_tags)

    st.write(st.session_state.selected_tags)
    # level 1 tags

    # top_key = st.selectbox("Top level key", options=["key1", "key2", "key3"])
    # if top_key == "key2":
    #     middle_key = st.selectbox("Second level key", options=["key11", "key22"])

    #     if middle_key == "key11":
    #         st.selectbox("Third level key", options=["key111"])

    st.write(tags)


def make_main_page():
    if "form_action" not in st.session_state:
        st.session_state.form_action = None

    with st.expander("", expanded=True):
        col1, col2, col3 = st.columns([1, 1, 1])

        with st.form("figure_configuration_form"):
            with col1:
                tooltip = st.selectbox("Tooltip", [])

            with col3:
                if st.form_submit_button("🔄"):
                    st.session_state.form_action = "refresh"

    if st.session_state.form_action == "refresh":
        # draw plot
        st.session_state.form_action = None


def make_dashboard(
    workdir: str | Path,
    data_products_filename: str = DATA_PRODUCTS_FNAME_DEFAULT,
):
    start = time.perf_counter()

    workdir = Path(workdir).resolve()

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
        make_sidebar(workdir=workdir)

    # make_main_page()

    with st.sidebar:
        st.caption(f"Site built in {time.perf_counter()-start:.2f} seconds")


def main():
    """To run use

    streamlit run src/trendify/streamlit.py
    """
    make_theme()
    make_dashboard(
        workdir=Path("sample_data/trendify"),
        data_products_filename="data_products.json",
    )


if __name__ == "__main__":
    main()
