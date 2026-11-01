import os
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env', override=False)

@dataclass
class Settings:
    database_path: Path = field(default_factory=lambda: Path(os.getenv('DATABASE_PATH', str(ROOT/'data/processed/store.sqlite'))))
    source_path: Path = ROOT/'data/source/base_organizada.xlsx'
    policy_path: Path = ROOT/'data/source/politicas_da_loja.pdf'
    openai_api_key: str = field(default_factory=lambda: os.getenv('OPENAI_API_KEY', ''))
    openai_model: str = field(default_factory=lambda: os.getenv('OPENAI_MODEL', ''))
    openai_base_url: str = field(default_factory=lambda: os.getenv('OPENAI_BASE_URL', ''))
    meta_access_token: str = field(default_factory=lambda: os.getenv('META_ACCESS_TOKEN', ''))
    meta_phone_number_id: str = field(default_factory=lambda: os.getenv('META_PHONE_NUMBER_ID', ''))
    meta_waba_id: str = field(default_factory=lambda: os.getenv('META_WABA_ID', ''))
    meta_verify_token: str = field(default_factory=lambda: os.getenv('META_VERIFY_TOKEN', ''))
    meta_app_secret: str = field(default_factory=lambda: os.getenv('META_APP_SECRET', ''))
    meta_graph_api_version: str = field(default_factory=lambda: os.getenv('META_GRAPH_API_VERSION', ''))
    app_env: str = field(default_factory=lambda: os.getenv('APP_ENV', 'local'))
    meta_dry_run: bool = field(default_factory=lambda: os.getenv('META_DRY_RUN', 'true').lower() != 'false')
    assistant_name: str = field(default_factory=lambda: os.getenv('ASSISTANT_NAME', 'Mel'))
    max_tool_calls: int = 8
    lease_seconds: int = 600
    max_attempts: int = 3
    request_timeout: int = 30

    def require_llm(self):
        if not self.openai_api_key or not self.openai_model:
            raise ValueError('Configure OPENAI_API_KEY e OPENAI_MODEL no .env.')
