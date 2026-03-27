from pathlib import Path
from typing import Callable, Optional

from aqt_connector import ArnicaConfig as BaseArnicaConfig

from qiskit_aqt_provider.persistence import get_store_path


class ArnicaConfig(BaseArnicaConfig):
    """Configuration for the SDK.

    Attributes:
        arnica_url (str): the base URL of the Arnica API. Defaults to "https://arnica.aqt.eu/api".
        client_id (str | None): the ID to use for authentication with client credentials. Defaults
            to None.
        client_secret (str | None): the secret to use for authentication with client credentials.
            Defaults to None.
        store_access_token (bool): when True, the access (and any refresh) token will be persisted
            to the ``store_path`` passed at initialisation. Defaults to True.
        oidc_config (object): configuration for the OIDC provider. You will not
            normally need to modify this.
    """

    def __init__(
        self,
        store_path: Optional[Path] = None,
        store_path_resolver: Callable[[Optional[Path]], Path] = get_store_path,
    ) -> None:
        """Initializes the configuration.

        Args:
            store_path: Local persistent storage directory. Defaults to a standard cache directory.
            store_path_resolver: A function that takes the provided store_path and resolves it to a
                path to use for storage. Defaults to the get_store_path function, which resolves the
                store path to a default location if None is provided.
        """
        super().__init__(store_path_resolver(store_path))
