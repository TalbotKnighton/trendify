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
