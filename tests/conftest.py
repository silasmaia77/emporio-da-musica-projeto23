import pytest
from src.config import Settings
from src.data.importer import import_data

@pytest.fixture
def settings(tmp_path):
    s=Settings(database_path=tmp_path/'test.sqlite',meta_phone_number_id='phone-test',meta_waba_id='waba-test',meta_app_secret='test-secret',meta_verify_token='test-verify',meta_dry_run=True,openai_model='test-model',openai_api_key='')
    import_data(s)
    return s
