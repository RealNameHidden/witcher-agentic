"""Pass a generated test key to ARM through a private temporary parameter file."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import tempfile

parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=["validate", "deploy"])
parser.add_argument("--image", required=True)
args = parser.parse_args()
key_path = Path(".azure/test-access.txt")
if not key_path.exists():
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        stream.write(secrets.token_urlsafe(32))
parameters = {
    "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentParameters.json#",
    "contentVersion": "1.0.0.0",
    "parameters": {"image": {"value": args.image}, "accessKey": {"value": key_path.read_text().strip()}},
}
with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as stream:
    json.dump(parameters, stream)
    stream.flush()
    subprocess.run([
        "az", "deployment", "group", "validate" if args.mode == "validate" else "create",
        "--subscription", "296247d8-59ad-4429-8a9b-7f153faebf2d",
        "--resource-group", "rg-witcher-test", "--name", "witcher-app",
        "--template-file", "infra/app.bicep", "--parameters", "@" + stream.name,
        "--query", "{state:properties.provisioningState,outputs:properties.outputs}", "-o", "json",
    ], check=True)
