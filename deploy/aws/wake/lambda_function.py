"""Puerta de entrada de LUCA en AWS (Lambda con Function URL). Guía: deploy/aws/README.md.

The EC2 instance stops itself after an hour without use, and a stopped machine can't answer, so students
always enter through this function's URL:
- instance running and the app healthy: redirect to the app (LUCA_APP_URL);
- stopped: a page with a "Despertar a Luca" button. Waking needs a POST so crawlers that hit the URL
  don't keep the server on;
- starting, or running while the app boots: a page that reloads itself until the app answers.

Runtime: Python 3.13 (boto3 comes with it). Env: LUCA_INSTANCE_ID, LUCA_APP_URL (e.g. https://52.1.2.3).
"""

import html
import os
import urllib.request

_ec2 = None


def ec2():
    global _ec2
    if _ec2 is None:
        import boto3

        _ec2 = boto3.client("ec2")
    return _ec2


def instance_state(instance_id: str) -> str:
    reservations = ec2().describe_instances(InstanceIds=[instance_id])["Reservations"]
    return reservations[0]["Instances"][0]["State"]["Name"]


def app_ready(app_url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{app_url}/healthz", timeout=3) as response:
            return response.status == 200
    except (OSError, ValueError):  # connection refused, timeout, TLS not ready yet
        return False


HEADERS = {
    "Content-Type": "text/html; charset=utf-8",
    "Cache-Control": "no-store",
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; "
                               "frame-ancestors 'none'; base-uri 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}

PAGES = {
    "stopped": ("Luca está dormida",
                "Se apaga sola cuando nadie la usa. Despertarla tarda uno o dos minutos.",
                '<form method="post" action="/"><button type="submit">Despertar a Luca</button></form>'),
    "starting": ("Luca se está despertando…",
                 "Suele tardar uno o dos minutos. Esta página se actualiza sola y te lleva cuando esté lista.", ""),
    "stopping": ("Luca se está apagando",
                 "En un momento vas a poder despertarla. Esta página se actualiza sola.", ""),
    "unavailable": ("Luca no está disponible", "Avisale al equipo docente.", ""),
}

TEMPLATE = """<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{refresh}<title>LUCA</title>
<style>
body {{ font-family: system-ui, sans-serif; display: grid; place-items: center; min-height: 90vh; margin: 0;
       background: #f5f6f8; color: #1f2933; text-align: center; }}
main {{ max-width: 32rem; padding: 2rem; }}
button {{ font-size: 1.1rem; padding: .75rem 1.5rem; border: 0; border-radius: .5rem; background: #2563eb;
         color: #fff; cursor: pointer; }}
</style>
</head>
<body><main><h1>{title}</h1><p>{text}</p>{action}</main></body>
</html>
"""


def page(kind: str, status: int = 200) -> dict:
    title, text, action = PAGES[kind]
    refresh = '<meta http-equiv="refresh" content="5">\n' if kind in ("starting", "stopping") else ""
    body = TEMPLATE.format(refresh=refresh, title=html.escape(title), text=html.escape(text), action=action)
    return {"statusCode": status, "headers": HEADERS, "body": body}


def redirect(location: str, status: int) -> dict:
    return {"statusCode": status, "headers": {"Location": location, "Cache-Control": "no-store"}, "body": ""}


def lambda_handler(event, context):
    instance_id = os.environ["LUCA_INSTANCE_ID"]
    app_url = os.environ["LUCA_APP_URL"].rstrip("/")
    method = event["requestContext"]["http"]["method"]
    if event.get("rawPath", "/") != "/":
        return {"statusCode": 404, "headers": {"Content-Type": "text/plain"}, "body": "No encontrado"}
    if method not in ("GET", "HEAD", "POST"):
        return {"statusCode": 405, "headers": {"Allow": "GET, POST"}, "body": ""}

    state = instance_state(instance_id)
    if method == "POST":
        if state == "stopped":
            ec2().start_instances(InstanceIds=[instance_id])
            print(f"Starting {instance_id}")
        return redirect("/", 303)  # back to GET: shows "despertando" and polls from there

    if state == "running" and app_ready(app_url):
        return redirect(f"{app_url}/", 302)
    if state in ("pending", "running"):
        return page("starting")
    if state in ("stopping", "shutting-down"):
        return page("stopping")
    if state == "stopped":
        return page("stopped")
    return page("unavailable", 503)
