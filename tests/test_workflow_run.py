import json
from fastapi.testclient import TestClient
from app.main import app
import pytest
from app.routers.auth import validate_credentials

def override_validate_credentials():
    return True

app.dependency_overrides[validate_credentials] = override_validate_credentials

client = TestClient(app)

def test_workflow_run():
    response = client.post("/assays/1/run")
    print(response.status_code)
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

    # if run it in airflow interface. set json config to:
    # {"assay_id": 1}
