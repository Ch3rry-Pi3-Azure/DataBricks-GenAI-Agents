import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULTS = {
    "resource_group_name_prefix": "rg-dbgenai",
    "location": "eastus2",
    "workspace_name_prefix": "adb-genai",
    "databricks_sku": "premium",
    "account_id": "24237807-b0da-4ee9-8908-110accb095ca",
    "metastore_id": "metastore_azure_eastus2",
    "default_catalog_name": "main",
    "use_ml_runtime": True,
    "data_security_mode": "SINGLE_USER",
    "spark_version": "16.4.x-scala2.13",
    "node_type_id": "Standard_D2ads_v6",
    "workspace_base_path": "/Shared/genai-agents",
    "notebook_name": "driver",
    "job_name": "GenAI Agents Driver Job",
}

ENV_KEYS = [
    "DATABRICKS_WORKSPACE_URL",
]

DATABRICKS_SP_APP_ID = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
AZ_FALLBACK_PATHS = [
    r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
    r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
]


def find_az():
    az_path = shutil.which("az")
    if az_path:
        return az_path
    for path in AZ_FALLBACK_PATHS:
        if Path(path).exists():
            return path
    return None


AZ_BIN = find_az()


def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    subprocess.check_call(cmd)


def run_capture(cmd):
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.check_output(cmd, text=True).strip()


def hcl_value(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace('"', '\\"')
    return f'"{escaped}"'


def write_tfvars(path, items):
    lines = [f"{key} = {hcl_value(value)}" for key, value in items]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def get_output(tf_dir, output_name):
    return run_capture(["terraform", f"-chdir={tf_dir}", "output", "-raw", output_name])


def normalize_databricks_host(host):
    if not host:
        return host
    return host if host.startswith("https://") else f"https://{host}"


def databricks_api(host, token, method, path, payload=None):
    url = f"{normalize_databricks_host(host).rstrip('/')}{path}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8")
        raise RuntimeError(f"Databricks API error {exc.code}: {detail}") from exc


def databricks_account_api(account_id, token, method, path, payload=None):
    base = "https://accounts.azuredatabricks.net"
    return databricks_api(base, token, method, f"/api/2.0/accounts/{account_id}{path}", payload)


def get_databricks_aad_token():
    if AZ_BIN is None:
        raise FileNotFoundError("Azure CLI not found. Install Azure CLI or ensure az is on PATH.")
    return run_capture(
        [
            AZ_BIN,
            "account",
            "get-access-token",
            "--resource",
            DATABRICKS_SP_APP_ID,
            "--query",
            "accessToken",
            "-o",
            "tsv",
        ]
    )


def get_workspace_id(account_id, token, workspace_name):
    response = databricks_account_api(account_id, token, "GET", "/workspaces")
    if isinstance(response, list):
        workspaces = response
    else:
        workspaces = response.get("workspaces", [])
    for workspace in workspaces or []:
        if workspace.get("workspace_name") == workspace_name:
            return workspace.get("workspace_id")
    return None


def get_metastore_id(account_id, token, metastore_name_or_id):
    if not metastore_name_or_id:
        return None
    if len(metastore_name_or_id) == 36 and metastore_name_or_id.count("-") == 4:
        return metastore_name_or_id
    response = databricks_account_api(account_id, token, "GET", "/metastores")
    if isinstance(response, list):
        metastores = response
    else:
        metastores = response.get("metastores", [])
    for metastore in metastores or []:
        if metastore.get("name") == metastore_name_or_id:
            return metastore.get("metastore_id")
    return None


def read_env_file(path):
    values = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def write_env_file(repo_root, workspace_url=None):
    env_path = repo_root / ".env"
    values = read_env_file(env_path)
    if workspace_url is not None:
        values["DATABRICKS_WORKSPACE_URL"] = normalize_databricks_host(workspace_url)
    if not values:
        return
    lines = [f"{key}={values[key]}" for key in ENV_KEYS if key in values]
    for key in sorted(values):
        if key in ENV_KEYS:
            continue
        lines.append(f"{key}={values[key]}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_rg_tfvars(rg_dir):
    items = [
        ("resource_group_name", None),
        ("resource_group_name_prefix", DEFAULTS["resource_group_name_prefix"]),
        ("location", DEFAULTS["location"]),
    ]
    write_tfvars(rg_dir / "terraform.tfvars", items)


def write_databricks_tfvars(databricks_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("location", DEFAULTS["location"]),
        ("workspace_name_prefix", DEFAULTS["workspace_name_prefix"]),
        ("sku", DEFAULTS["databricks_sku"]),
        ("managed_resource_group_name", None),
    ]
    write_tfvars(databricks_dir / "terraform.tfvars", items)


def write_metastore_tfvars(metastore_dir, workspace_id):
    token = get_databricks_aad_token()
    metastore_id = get_metastore_id(
        DEFAULTS["account_id"],
        token,
        DEFAULTS["metastore_id"],
    )
    if metastore_id is None:
        raise RuntimeError(f"Could not resolve metastore ID for {DEFAULTS['metastore_id']}.")
    items = [
        ("account_id", DEFAULTS["account_id"]),
        ("metastore_id", metastore_id),
        ("workspace_id", workspace_id),
        ("default_catalog_name", DEFAULTS["default_catalog_name"]),
    ]
    write_tfvars(metastore_dir / "terraform.tfvars", items)


def write_compute_tfvars(compute_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("use_ml_runtime", DEFAULTS["use_ml_runtime"]),
        ("spark_version", DEFAULTS["spark_version"]),
        ("node_type_id", DEFAULTS["node_type_id"]),
        ("data_security_mode", DEFAULTS["data_security_mode"]),
    ]
    write_tfvars(compute_dir / "terraform.tfvars", items)


def write_notebooks_tfvars(notebooks_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("workspace_base_path", DEFAULTS["workspace_base_path"]),
    ]
    write_tfvars(notebooks_dir / "terraform.tfvars", items)


def write_job_tfvars(job_dir, rg_name):
    items = [
        ("resource_group_name", rg_name),
        ("workspace_base_path", DEFAULTS["workspace_base_path"]),
        ("notebook_name", DEFAULTS["notebook_name"]),
        ("job_name", DEFAULTS["job_name"]),
    ]
    write_tfvars(job_dir / "terraform.tfvars", items)


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Deploy Terraform stacks for Databricks GenAI Agents.")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--rg-only", action="store_true", help="Deploy only the resource group stack")
        group.add_argument("--databricks-only", action="store_true", help="Deploy only the Databricks workspace stack")
        group.add_argument("--metastore-only", action="store_true", help="Deploy only the UC metastore assignment stack")
        group.add_argument("--compute-only", action="store_true", help="Deploy only the Databricks compute stack")
        group.add_argument("--notebooks-only", action="store_true", help="Deploy only the notebooks stack")
        group.add_argument("--job-only", action="store_true", help="Deploy only the Databricks job stack")
        args = parser.parse_args()

        repo_root = Path(__file__).resolve().parent.parent
        rg_dir = repo_root / "terraform" / "01_resource_group"
        databricks_dir = repo_root / "terraform" / "02_databricks_workspace"
        metastore_dir = repo_root / "terraform" / "03_uc_metastore_assignment"
        compute_dir = repo_root / "terraform" / "04_databricks_compute"
        notebooks_dir = repo_root / "terraform" / "05_notebooks"
        job_dir = repo_root / "terraform" / "06_job"

        if args.rg_only:
            write_rg_tfvars(rg_dir)
            run(["terraform", f"-chdir={rg_dir}", "init"])
            run(["terraform", f"-chdir={rg_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.databricks_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_databricks_tfvars(databricks_dir, rg_name)
            run(["terraform", f"-chdir={databricks_dir}", "init"])
            run(["terraform", f"-chdir={databricks_dir}", "apply", "-auto-approve"])
            workspace_url = get_output(databricks_dir, "databricks_workspace_url")
            write_env_file(repo_root, workspace_url=workspace_url)
            sys.exit(0)

        if args.metastore_only:
            run(["terraform", f"-chdir={databricks_dir}", "init"])
            workspace_name = get_output(databricks_dir, "databricks_workspace_name")
            token = get_databricks_aad_token()
            workspace_id = get_workspace_id(DEFAULTS["account_id"], token, workspace_name)
            if workspace_id is None:
                raise RuntimeError(f"Could not resolve workspace ID for {workspace_name}.")
            write_metastore_tfvars(metastore_dir, workspace_id)
            run(["terraform", f"-chdir={metastore_dir}", "init"])
            run(["terraform", f"-chdir={metastore_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.compute_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_compute_tfvars(compute_dir, rg_name)
            run(["terraform", f"-chdir={compute_dir}", "init"])
            run(["terraform", f"-chdir={compute_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.notebooks_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_notebooks_tfvars(notebooks_dir, rg_name)
            run(["terraform", f"-chdir={notebooks_dir}", "init"])
            run(["terraform", f"-chdir={notebooks_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        if args.job_only:
            run(["terraform", f"-chdir={rg_dir}", "init"])
            rg_name = get_output(rg_dir, "resource_group_name")
            write_job_tfvars(job_dir, rg_name)
            run(["terraform", f"-chdir={job_dir}", "init"])
            run(["terraform", f"-chdir={job_dir}", "apply", "-auto-approve"])
            sys.exit(0)

        write_rg_tfvars(rg_dir)
        run(["terraform", f"-chdir={rg_dir}", "init"])
        run(["terraform", f"-chdir={rg_dir}", "apply", "-auto-approve"])
        rg_name = get_output(rg_dir, "resource_group_name")

        write_databricks_tfvars(databricks_dir, rg_name)
        run(["terraform", f"-chdir={databricks_dir}", "init"])
        run(["terraform", f"-chdir={databricks_dir}", "apply", "-auto-approve"])
        workspace_url = get_output(databricks_dir, "databricks_workspace_url")
        workspace_name = get_output(databricks_dir, "databricks_workspace_name")

        token = get_databricks_aad_token()
        workspace_id = get_workspace_id(DEFAULTS["account_id"], token, workspace_name)
        if workspace_id is None:
            raise RuntimeError(f"Could not resolve workspace ID for {workspace_name}.")
        write_metastore_tfvars(metastore_dir, workspace_id)
        run(["terraform", f"-chdir={metastore_dir}", "init"])
        run(["terraform", f"-chdir={metastore_dir}", "apply", "-auto-approve"])

        write_compute_tfvars(compute_dir, rg_name)
        run(["terraform", f"-chdir={compute_dir}", "init"])
        run(["terraform", f"-chdir={compute_dir}", "apply", "-auto-approve"])

        write_notebooks_tfvars(notebooks_dir, rg_name)
        run(["terraform", f"-chdir={notebooks_dir}", "init"])
        run(["terraform", f"-chdir={notebooks_dir}", "apply", "-auto-approve"])

        write_job_tfvars(job_dir, rg_name)
        run(["terraform", f"-chdir={job_dir}", "init"])
        run(["terraform", f"-chdir={job_dir}", "apply", "-auto-approve"])
        write_env_file(repo_root, workspace_url=workspace_url)
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(exc.returncode)
