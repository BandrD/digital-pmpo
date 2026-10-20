import os
import ssl
from pathlib import Path

_BUNDLED_CA = Path(__file__).resolve().parents[1] / "certs" / "russian_trusted_root_ca.pem"


def max_ssl_context() -> ssl.SSLContext:
    """Доверять системным CA и корневому сертификату Минцифры.

    SSL_CERT_FILE только с этим корнем не используем: тогда отвалятся остальные HTTPS-вызовы.
    """
    context = ssl.create_default_context()
    env_path = os.getenv("MAX_ROOT_CA_PATH")
    if env_path:
        if not os.path.isfile(env_path):
            raise FileNotFoundError(f"MAX_ROOT_CA_PATH не найден: {env_path}")
        context.load_verify_locations(env_path)
        return context
    if _BUNDLED_CA.is_file():
        context.load_verify_locations(str(_BUNDLED_CA))
    return context
