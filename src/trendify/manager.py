class TrendifyManager:
    """
    Main class for managing Trendify data processing, indexing, and retrieval.
    """

    def __init__(
        self,
        output_dir: Path,
        data_assets_filename: str = DEFAULT_DATA_PRODUCTS_FILENAME,
    ):
        self.file_manager = TrendifyFileManager(output_dir)
        self.data_assets_filename = data_assets_filename
        self._index: Optional[TrendifyIndex] = None
        self._file_cache = {}
        self._max_cache_size = 20
        self.asset_spec_registry = ProductSpecRegistry()

    @property
    def index(self) -> TrendifyIndex:
        """Get the index, loading it if necessary."""
        if self._index is None:
            self._load_index()
        return self._index

    def _load_index(self) -> None:
        """Load the index from file or create a new one."""
        index_file = self.file_manager.index_file
        if index_file.exists():
            self._index = TrendifyIndex.model_validate_json(index_file.read_text())
        else:
            self._index = TrendifyIndex()

    def save_index(self) -> None:
        """Save the current index to file."""
        if self._index is not None:
            self.file_manager.index_file.write_text(
                self._index.model_dump_json(indent=2)
            )

    def _get_origin_id(self, input_dir: Path) -> str:
        """
        Generate a unique origin ID for an input directory.

        Args:
            input_dir: The input directory

        Returns:
            A string ID for the origin
        """
        # Use a combination of directory name and a hash of the absolute path
        dir_name = input_dir.name
        path_hash = hash(str(input_dir.resolve()))
        return f"{dir_name}_{path_hash % 10000:04d}"

    def process_origin_directory(
        self, input_dir: Path, asset_generator: AssetGenerator
    ) -> str:
        """
        Process a single origin directory and store its assets and asset specs.

        Args:
            input_dir: Input directory to process
            asset_generator: Function that generates assets and assets

        Returns:
            Origin ID for the processed directory
        """
        # Calculate origin ID
        origin_id = self._get_origin_id(input_dir)

        # Generate assets and assets for this directory
        try:
            asset_specs, assets = asset_generator(input_dir)
        except Exception as e:
            logger.error(f"Error processing directory {input_dir}: {e}")
            # Return origin ID even on failure to maintain consistent indexing
            return origin_id

        # Create origin directory
        origin_dir = self.file_manager.get_origin_dir(origin_id)

        # Create ProductsModel with metadata
        assets_model = AssetCollection.create(
            origin_id=origin_id, original_dir=str(input_dir), assets=assets
        )

        # Save assets model to origin directory
        asset_file = origin_dir.joinpath(self.data_assets_filename)
        asset_file.write_text(assets_model.model_dump_json(indent=2))

        # Process asset specs if any
        if asset_specs:
            for spec in asset_specs:
                self.asset_spec_registry.add_spec(spec)

            # Save asset specs to file
            self._save_asset_specs(asset_specs, origin_id)

        return origin_id

    def _save_asset_specs(self, asset_specs: List[ProductSpec], origin_id: str) -> None:
        """
        Save asset specifications to appropriate files.

        Args:
            asset_specs: List of asset specifications to save
            origin_id: Origin identifier for the specs
        """
        # Group specs by type
        specs_by_type = {}
        for spec in asset_specs:
            spec_type = spec.__class__.__name__
            if spec_type not in specs_by_type:
                specs_by_type[spec_type] = []
            specs_by_type[spec_type].append(spec)

        # Save each group to a separate file
        for spec_type, specs in specs_by_type.items():
            # Create file name based on origin
            spec_file = self.file_manager.get_spec_file(spec_type, origin_id)

            # Create collection and save
            spec_collection = SerializableCollection(items=specs)
            spec_file.write_text(spec_collection.model_dump_json(indent=2))

            # Add to index
            for i, spec in enumerate(specs):
                spec_id = f"{origin_id}_{spec_type}_{i}"
                self.index.add_spec(
                    spec_id=spec_id,
                    spec_type=spec_type,
                    file_path=str(spec_file.relative_to(self.file_manager)),
                    tag=spec.tag,
                )

    def process_origins(
        self,
        input_dirs: List[Path],
        asset_generator: AssetGenerator,
        n_procs: int = 1,
    ) -> List[str]:
        """
        Process multiple origin directories, optionally in parallel.

        Args:
            input_dirs: List of input directories to process
            asset_generator: Function to generate assets from each directory
            n_procs: Number of parallel processes to use

        Returns:
            List of origin IDs for the processed directories
        """
        # Create partial function with fixed parameters
        process_func = partial(
            self.process_origin_directory, asset_generator=asset_generator
        )

        # Process directories, possibly in parallel
        if n_procs > 1:
            with ProcessPoolExecutor(max_workers=n_procs) as executor:
                origin_ids = list(executor.map(process_func, input_dirs))
        else:
            origin_ids = [process_func(d) for d in input_dirs]

        return origin_ids

    def build_index(self) -> None:
        """
        Build a comprehensive index by scanning the asset directory structure.
        """
        # Create a new index
        self._index = TrendifyIndex()

        # Scan origin directories
        origin_dirs = list(self.file_manager.assets_by_origin_dir.glob("*/"))

        for origin_dir in origin_dirs:
            origin_id = origin_dir.name

            # Check if asset file exists
            asset_file = origin_dir.joinpath(self.data_assets_filename)
            if not asset_file.exists():
                continue

            file_path = str(asset_file.relative_to(self.file_manager))

            # Load asset model to get metadata
            assets_model = self._load_assets_file(file_path)

            # Extract original directory from metadata
            original_dir = assets_model.metadata.original_dir

            # Add origin to index
            self.index.origins[origin_id] = {
                "asset_ids": [],
                "directory": original_dir,
            }

            # Index each asset
            for position, asset in enumerate(assets_model.assets):
                # Generate asset ID
                asset_id = f"{origin_id}_{asset.asset_type}_{position}"

                # Add to index
                self.index.add_asset(
                    asset_id=asset_id,
                    asset_type=asset.asset_type,
                    file_path=file_path,
                    position=position,
                    origin=origin_id,
                    tags=asset.tags,
                )

        # Scan spec files
        for spec_type_dir in self.file_manager.specs_dir.glob("*/"):
            spec_type = spec_type_dir.name

            for spec_file in spec_type_dir.glob("*.json"):
                # Extract origin ID from filename
                origin_id = spec_file.stem

                file_path = str(spec_file.relative_to(self.file_manager))

                # Load specs
                try:
                    with open(spec_file, "r") as f:
                        spec_data = json.load(f)

                    # Index each spec
                    for i, spec_data in enumerate(spec_data.get("items", [])):
                        tag = spec_data.get("tag")
                        if tag:
                            spec_id = f"{origin_id}_{spec_type}_{i}"
                            self.index.add_spec(
                                spec_id=spec_id,
                                spec_type=spec_type,
                                file_path=file_path,
                                tag=tag,
                            )
                except Exception as e:
                    logger.error(f"Error indexing spec file {spec_file}: {e}")

        # Save the index
        self.save_index()

    def _load_assets_file(self, file_path: str) -> AssetCollection:
        """
        Load a assets file with caching.

        Args:
            file_path: Path to the assets file relative to the file manager root

        Returns:
            The loaded ProductsModel
        """
        # Check cache first
        if file_path in self._file_cache:
            return self._file_cache[file_path]

        # Load file
        absolute_path = self.file_manager.joinpath(file_path)
        with open(absolute_path, "r") as f:
            assets_model = AssetCollection.model_validate_json(f.read())

        # Add to cache
        self._file_cache[file_path] = assets_model

        # Manage cache size
        if len(self._file_cache) > self._max_cache_size:
            # Remove oldest entry
            self._file_cache.pop(next(iter(self._file_cache)))

        return assets_model

    def get_assets_by_tag(
        self, tag: Tag, asset_type: Optional[Type[P]] = None
    ) -> List[P]:
        """
        Retrieve assets matching a tag and optional type.

        Args:
            tag: The tag to match
            asset_type: Optional type filter

        Returns:
            List of matching assets
        """
        # Get asset IDs for this tag
        asset_ids = self.index.get_asset_ids_by_tag(tag)

        # Group by file to minimize I/O
        file_positions = {}
        for asset_id in asset_ids:
            asset_info = self.index.assets[asset_id]

            # Filter by type if specified
            if asset_type is not None:
                if asset_info["type"] != asset_type.__name__:
                    continue

            file_path = asset_info["file"]
            if file_path not in file_positions:
                file_positions[file_path] = []

            file_positions[file_path].append(asset_info["position"])

        # Load assets from files
        assets = []
        for file_path, positions in file_positions.items():
            assets_model = self._load_assets_file(file_path)

            for position in positions:
                asset = assets_model.assets[position]
                if asset_type is None or isinstance(asset, asset_type):
                    assets.append(asset)

        return assets

    def get_assets_by_origin(
        self, origin_id: str, asset_type: Optional[Type[P]] = None
    ) -> List[P]:
        """
        Retrieve assets from a specific origin.

        Args:
            origin_id: The origin identifier
            asset_type: Optional type filter

        Returns:
            List of matching assets
        """
        # Get asset IDs for this origin
        asset_ids = self.index.get_asset_ids_by_origin(origin_id)

        # Group by file (should be just one file for an origin)
        file_positions = {}
        for asset_id in asset_ids:
            asset_info = self.index.assets[asset_id]

            # Filter by type if specified
            if asset_type is not None:
                if asset_info["type"] != asset_type.__name__:
                    continue

            file_path = asset_info["file"]
            if file_path not in file_positions:
                file_positions[file_path] = []

            file_positions[file_path].append(asset_info["position"])

        # Load assets from files
        assets = []
        for file_path, positions in file_positions.items():
            assets_model = self._load_assets_file(file_path)

            for position in positions:
                asset = assets_model.assets[position]
                if asset_type is None or isinstance(asset, asset_type):
                    assets.append(asset)

        return assets

    def get_asset_by_id(self, asset_id: str) -> Optional[Asset]:
        """
        Retrieve a specific asset by ID.

        Args:
            asset_id: The asset ID

        Returns:
            The asset if found, None otherwise
        """
        if asset_id not in self.index.assets:
            return None

        asset_info = self.index.assets[asset_id]
        file_path = asset_info["file"]
        position = asset_info["position"]

        assets_model = self._load_assets_file(file_path)
        return assets_model.assets[position]

    def get_asset_specs_by_tag(
        self, tag: Tag, spec_type: Optional[Type[A]] = None
    ) -> List[A]:
        """
        Retrieve asset specifications matching a tag and optional type.

        Args:
            tag: The tag to match
            spec_type: Optional type filter

        Returns:
            List of matching specifications
        """
        # Get from registry if already loaded
        if spec_type:
            spec = self.asset_spec_registry.get_spec(spec_type, tag)
            return [spec] if spec else []
        else:
            return self.asset_spec_registry.get_specs_by_tag(tag)

        # Alternatively, load from index and files
        # This would be implemented similarly to get_assets_by_tag

    def process_data(
        self,
        input_dirs: List[Path],
        asset_generator: AssetGenerator,
        n_procs: int = 1,
        rebuild_index: bool = True,
    ) -> None:
        """
        Process data from input directories, generate assets and build index.

        This is the main entry point for data processing.

        Args:
            input_dirs: List of directories containing raw data
            asset_generator: Function to generate assets from each directory
            n_procs: Number of parallel processes to use
            rebuild_index: Whether to rebuild the index after processing
        """
        logger.info(
            f"Processing {len(input_dirs)} directories with {n_procs} processes"
        )

        # Process each origin directory
        self.process_origins(
            input_dirs=input_dirs, asset_generator=asset_generator, n_procs=n_procs
        )

        # Build comprehensive index
        if rebuild_index:
            logger.info("Building index")
            self.build_index()

        logger.info("Data processing complete")

    def get_all_tags(self) -> Set[str]:
        """
        Get all tags in the index.

        Returns:
            Set of all tags
        """
        return set(self.index.tags.keys())

    def get_all_origins(self) -> Set[str]:
        """
        Get all origin IDs in the index.

        Returns:
            Set of all origin IDs
        """
        return set(self.index.origins.keys())

    def get_tag_statistics(self) -> Dict[str, Dict[str, int]]:
        """
        Get statistics about tags.

        Returns:
            Dictionary with tag statistics
        """
        stats = {}
        for tag, info in self.index.tags.items():
            stats[tag] = {
                "asset_count": len(info["asset_ids"]),
                "spec_count": len(info["spec_ids"]),
                "asset_count": len(info["asset_files"]),
            }
        return stats

    def get_origin_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get statistics about origins.

        Returns:
            Dictionary with origin statistics
        """
        stats = {}
        for origin_id, info in self.index.origins.items():
            stats[origin_id] = {
                "asset_count": len(info["asset_ids"]),
                "directory": info["directory"],
            }
        return stats

    def clear_cache(self) -> None:
        """Clear the file cache to free memory."""
        self._file_cache.clear()

    def create_static_assets(
        self,
        tags: Optional[List[Tag]] = None,
        n_procs: int = 1,
        renderer_class=None,  # Default to MatplotlibRenderer
    ) -> None:
        """
        Create static assets for the given tags.

        Args:
            tags: List of tags for which to create assets (defaults to all tags)
            n_procs: Number of parallel processes to use
            renderer_class: The renderer class to use (defaults to MatplotlibRenderer)
        """
        if renderer_class is None:
            from trendify.renderers import MatplotlibRenderer

            renderer_class = MatplotlibRenderer

        # Use all tags if none specified
        if tags is None:
            tags = list(self.get_all_tags())

        # Create renderer
        renderer = renderer_class(self)

        # Process tags
        if n_procs > 1:
            # Process in parallel
            with ProcessPoolExecutor(max_workers=n_procs) as executor:
                executor.map(renderer.render_tag, tags)
        else:
            # Process sequentially
            for tag in tags:
                renderer.render_tag(tag)

    def serve_dashboard(
        self,
        host: str = "127.0.0.1",
        port: int = 8050,
        debug: bool = False,
        title: str = "Trendify Dashboard",
    ) -> None:
        """
        Serve an interactive dashboard for exploring data assets.

        Args:
            host: Host address to bind to
            port: Port to listen on
            debug: Whether to run in debug mode
            title: Dashboard title
        """
        from trendify.dashboard import create_dashboard

        app = create_dashboard(self, title=title)
        app.run_server(host=host, port=port, debug=debug)
