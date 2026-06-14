import logging

from dragiter.domain.models.chunk import Chunk

logger = logging.getLogger(__name__)


class Material():
    def __init__(self, chunks: list[Chunk]):
        """Initialise the configuration object and load settings."""
        # super().__init__()

        self._chunks: list[Chunk] = chunks

        # # local vars
        # material_config_dict: dict[str, dict] = {}
        # mf: Path = Path(config.material_file) if config.material_file else None
        #
        # if mf is not None and mf.exists():
        #     try:
        #         material_config_dict = read_from_toml(mf)
        #         self._chunks = self._process_markdown_configs(material_config_dict)
        #     except Exception as e:
        #         raise MaterialError(f"Failed to load material chunks, defined in file {mf}.") from e
        #
        # if config.debug:
        #     print(f"Loaded {len(self._chunks)} chunks.")

    @property
    def chunks(self):
        return self._chunks

    def __repr__(self):
        # Das hier wird im Logger angezeigt
        return f"Material(chunks length ='{len(self._chunks)}'"
