"""Wake-up front door for the EC2 deployment (deploy/aws/wake), with EC2 and the app's health check faked."""

import importlib.util
from pathlib import Path

import pytest

LAMBDA = Path(__file__).resolve().parent.parent / "deploy" / "aws" / "wake" / "lambda_function.py"


class FakeEC2:
    def __init__(self, state):
        self.state = state
        self.started = []

    def describe_instances(self, InstanceIds):
        return {"Reservations": [{"Instances": [{"InstanceId": InstanceIds[0], "State": {"Name": self.state}}]}]}

    def start_instances(self, InstanceIds):
        self.started += InstanceIds
        self.state = "pending"


@pytest.fixture
def wake(monkeypatch):
    spec = importlib.util.spec_from_file_location("lambda_function", LAMBDA)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setenv("LUCA_INSTANCE_ID", "i-0abc")
    monkeypatch.setenv("LUCA_APP_URL", "https://52.1.2.3/")
    return module


def _call(module, method="GET", path="/"):
    return module.handler({"rawPath": path, "requestContext": {"http": {"method": method}}}, None)


def _setup(module, monkeypatch, state, ready=False):
    fake = FakeEC2(state)
    monkeypatch.setattr(module, "_ec2", fake)
    monkeypatch.setattr(module, "app_ready", lambda url: ready)
    return fake


def test_running_and_healthy_redirects_to_the_app(wake, monkeypatch):
    _setup(wake, monkeypatch, "running", ready=True)
    response = _call(wake)
    assert response["statusCode"] == 302 and response["headers"]["Location"] == "https://52.1.2.3/"


def test_visiting_a_stopped_instance_does_not_start_it(wake, monkeypatch):
    fake = _setup(wake, monkeypatch, "stopped")
    response = _call(wake)
    assert response["statusCode"] == 200 and "Despertar a Luca" in response["body"]
    assert fake.started == []  # crawlers only GET: they must not keep the server on


def test_the_button_starts_it_and_the_page_polls_until_ready(wake, monkeypatch):
    fake = _setup(wake, monkeypatch, "stopped")
    response = _call(wake, "POST")
    assert response["statusCode"] == 303 and fake.started == ["i-0abc"]
    page = _call(wake)
    assert "despertando" in page["body"] and 'http-equiv="refresh"' in page["body"]
    fake.state = "running"  # booted, but the app isn't answering yet
    assert "despertando" in _call(wake)["body"]


def test_posting_while_running_does_not_start_again(wake, monkeypatch):
    fake = _setup(wake, monkeypatch, "running", ready=True)
    assert _call(wake, "POST")["statusCode"] == 303 and fake.started == []


def test_stopping_and_unknown_paths(wake, monkeypatch):
    _setup(wake, monkeypatch, "stopping")
    assert "apagando" in _call(wake)["body"]
    assert _call(wake, path="/wp-login.php")["statusCode"] == 404
    assert _call(wake, "DELETE")["statusCode"] == 405
