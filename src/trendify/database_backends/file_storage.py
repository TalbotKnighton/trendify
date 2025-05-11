from file_manager import FileManager, mkdir, Path


class TrendifyFileManager(FileManager):
    """
    File manager specifically for Trendify project structure.

    Provides properties for all standard directories and paths
    in the Trendify project.
    """

    def __new__(cls, path, *args, **kwargs):
        return super(TrendifyFileManager, cls).__new__(cls, path, *args, **kwargs)

    @mkdir
    @property
    def index_dir(self):
        """Directory for index files."""
        return self / "index"

    @property
    def index_file(self):
        """Main index file."""
        return self.index_dir / "trendify_index.json"

    @mkdir
    @property
    def products_dir(self):
        """Root directory for all products."""
        return self / "products"

    @mkdir
    @property
    def products_by_origin_dir(self):
        """Directory for products organized by origin."""
        return self.products_dir / "by_origin"

    @mkdir
    @property
    def products_by_tag_dir(self):
        """Directory for products organized by tag."""
        return self.products_dir / "by_tag"

    def get_origin_dir(self, origin_id: str):
        """Get directory for a specific origin."""
        path = self.products_by_origin_dir / origin_id
        return mkdir(path)

    def get_tag_dir(self, tag: str):
        """Get directory for a specific tag."""
        path = self.products_by_tag_dir / tag
        return mkdir(path)

    @mkdir
    @property
    def specs_dir(self):
        """Root directory for all specifications."""
        return self / "specs"

    @mkdir
    @property
    def figure_specs_dir(self):
        """Directory for figure specifications."""
        return self.specs_dir / "figure_specs"

    @mkdir
    @property
    def grid_specs_dir(self):
        """Directory for grid specifications."""
        return self.specs_dir / "grid_specs"

    @mkdir
    @property
    def assets_dir(self):
        """Root directory for all assets."""
        return self / "assets"

    @mkdir
    @property
    def static_assets_dir(self):
        """Directory for static assets."""
        return self.assets_dir / "static"

    @mkdir
    @property
    def interactive_assets_dir(self):
        """Directory for interactive assets."""
        return self.assets_dir / "interactive"

    def get_static_asset_dir(self, tag: str):
        """Get static asset directory for a specific tag."""
        path = self.static_assets_dir / tag
        return mkdir(path)

    def get_origin_product_file(
        self, origin_id: str, filename: str = "data_products.json"
    ):
        """Get the product file for a specific origin."""
        return self.get_origin_dir(origin_id) / filename

    def get_spec_file(self, spec_type: str, name: str):
        """Get a specification file of a given type."""
        spec_dir = self.specs_dir / spec_type
        mkdir(spec_dir)
        return spec_dir / f"{name}.json"


# Example usage
if __name__ == "__main__":
    # Basic mkdir usage
    data_dir = mkdir("./data")
    print(f"Created {data_dir}")

    # FileManager with property
    class ProjectFiles(FileManager):
        @mkdir
        @property
        def output(self):
            return self / "output"

        @mkdir
        @property
        def logs(self):
            return self / "logs"

    project = ProjectFiles("./my_project")
    print(f"Created {project.output}")
    print(f"Created {project.logs}")

    # TrendifyFileManager usage
    trendify = TrendifyFileManager("./trendify_output")
    origin_dir = trendify.get_origin_dir("origin123")
    product_file = trendify.get_origin_product_file("origin123")
    spec_file = trendify.get_spec_file("figure_specs", "performance_plot")

    print(f"Origin dir: {origin_dir}")
    print(f"Product file: {product_file}")
    print(f"Spec file: {spec_file}")


class AssetCollection(SerializableModel):
    """Container for data assets with metadata."""

    metadata: AssetMetadata
    assets: List[Asset]  # List of serializable data assets

    @classmethod
    def create(cls, origin_id: str, original_dir: str, assets: List[Asset]):
        """Create a ProductsModel with automatically generated metadata."""

        # Count asset types
        type_counts = {}
        for asset in assets:
            type_name = asset.asset_type
            type_counts[type_name] = type_counts.get(type_name, 0) + 1

        # Count tags
        tag_counts = {}
        for asset in assets:
            for tag in asset.tags:
                tag_str = str(tag)
                tag_counts[tag_str] = tag_counts.get(tag_str, 0) + 1

        # Create metadata
        metadata = AssetMetadata(
            origin_id=origin_id,
            original_dir=str(original_dir),
            asset_count=len(assets),
            asset_type_counts=type_counts,
            tag_counts=tag_counts,
        )

        return cls(metadata=metadata, assets=assets)

    def get_assets_by_type(self, asset_type: Type[P]) -> List[P]:
        """Filter assets by type."""
        return [p for p in self.assets if isinstance(p, asset_type)]

    def get_assets_by_tag(self, tag: Tag) -> List[Asset]:
        """Filter assets by tag."""
        return [p for p in self.assets if tag in p.tags]


class TrendifyIndex(SerializableModel):
    """
    Comprehensive index for trendify assets and specs.

    This keeps track of all assets, their origins, tags, and locations.
    """

    tags: Dict[str, Dict[str, List[str]]] = {}
    origins: Dict[str, Dict[str, Any]] = {}
    assets: Dict[str, Dict[str, Any]] = {}
    specs: Dict[str, Dict[str, Any]] = {}

    def add_asset(
        self,
        asset_id: str,
        asset_type: str,
        file_path: str,
        position: int,
        origin: str,
        tags: List[Tag],
    ):
        """Add a asset to the index."""
        # Convert tags to strings for use as keys
        str_tags = [str(tag) for tag in tags]

        # Update assets index
        self.assets[asset_id] = {
            "type": asset_type,
            "file": file_path,
            "position": position,
            "origin": origin,
            "tags": str_tags,
        }

        # Update tags index
        for tag in str_tags:
            if tag not in self.tags:
                self.tags[tag] = {"asset_ids": [], "spec_ids": [], "asset_files": []}

            if asset_id not in self.tags[tag]["asset_ids"]:
                self.tags[tag]["asset_ids"].append(asset_id)

        # Update origins index
        if origin not in self.origins:
            self.origins[origin] = {"asset_ids": [], "directory": ""}

        if asset_id not in self.origins[origin]["asset_ids"]:
            self.origins[origin]["asset_ids"].append(asset_id)

    def add_spec(self, spec_id: str, spec_type: str, file_path: str, tag: Tag):
        """Add a specification to the index."""
        # Convert tag to string for use as key
        str_tag = str(tag)

        # Update specs index
        self.specs[spec_id] = {"type": spec_type, "file": file_path, "tag": str_tag}

        # Update tags index
        if str_tag not in self.tags:
            self.tags[str_tag] = {"asset_ids": [], "spec_ids": [], "asset_files": []}

        if spec_id not in self.tags[str_tag]["spec_ids"]:
            self.tags[str_tag]["spec_ids"].append(spec_id)

    def add_asset_file(self, file_path: str, tag: Tag):
        """Add an asset file to the index."""
        # Convert tag to string for use as key
        str_tag = str(tag)

        # Update tags index
        if str_tag not in self.tags:
            self.tags[str_tag] = {"asset_ids": [], "spec_ids": [], "asset_files": []}

        if file_path not in self.tags[str_tag]["asset_files"]:
            self.tags[str_tag]["asset_files"].append(file_path)

    def get_asset_ids_by_tag(self, tag: Tag) -> List[str]:
        """Get all asset IDs associated with a tag."""
        str_tag = str(tag)
        if str_tag not in self.tags:
            return []

        return self.tags[str_tag]["asset_ids"]

    def get_asset_ids_by_origin(self, origin: str) -> List[str]:
        """Get all asset IDs associated with an origin."""
        if origin not in self.origins:
            return []

        return self.origins[origin]["asset_ids"]

    def get_spec_ids_by_tag(self, tag: Tag) -> List[str]:
        """Get all spec IDs associated with a tag."""
        str_tag = str(tag)
        if str_tag not in self.tags:
            return []

        return self.tags[str_tag]["spec_ids"]
