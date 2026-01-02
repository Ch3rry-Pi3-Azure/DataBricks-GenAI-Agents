import argparse
import json
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path


def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    subprocess.check_call(cmd)

AZ_FALLBACK_PATHS = [
    r"C:\Program Files (x86)\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
    r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd",
]

DATABRICKS_SP_APP_ID = "2ff814a6-3304-4ab8-85cb-cd0e6f879c1d"
WORKSPACE_BASE_PATH = "/Shared/genai-agents"
WORKSPACE_FILES_TO_DELETE = ["agent.py", "agents.py"]


def find_az():
    az_path = shutil.which("az")
    if az_path:
        return az_path
    for path in AZ_FALLBACK_PATHS:
        if Path(path).exists():
            return path
    return None


AZ_BIN = find_az()


def run_capture(cmd):
    print(f"\n$ {' '.join(cmd)}")
    return subprocess.check_output(cmd, text=True).strip()


def get_output(tf_dir, output_name):
    return run_capture(["terraform", f"-chdir={tf_dir}", "output", "-raw", output_name])


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


def ensure_rg_tfvars(tf_dir, rg_name):
    tfvars_path = tf_dir / "terraform.tfvars"
    if tfvars_path.exists():
        return
    if rg_name is None:
        return
    write_tfvars(tfvars_path, [("resource_group_name", rg_name)])


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


def cleanup_workspace_files(workspace_url):
    token = get_databricks_aad_token()
    try:
        response = databricks_api(
            workspace_url,
            token,
            "GET",
            f"/api/2.0/workspace/list?path={WORKSPACE_BASE_PATH}",
        )
    except RuntimeError as exc:
        print(f"Skipping workspace cleanup: {exc}")
        return

    objects = response.get("objects", [])
    for obj in objects:
        path = obj.get("path")
        if not path:
            continue
        if any(path.endswith(f"/{name}") for name in WORKSPACE_FILES_TO_DELETE):
            databricks_api(
                workspace_url,
                token,
                "POST",
                "/api/2.0/workspace/delete",
                {"path": path, "recursive": False},
            )
            print(f"Deleted workspace file: {path}")


if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser(description="Destroy Terraform stacks for Databricks GenAI Agents.")
        group = parser.add_mutually_exclusive_group()
        group.add_argument("--rg-only", action="store_true", help="Destroy only the resource group stack")
        group.add_argument("--databricks-only", action="store_true", help="Destroy only the Databricks workspace stack")
        group.add_argument("--metastore-only", action="store_true", help="Destroy only the UC metastore assignment stack")
        group.add_argument("--compute-only", action="store_true", help="Destroy only the Databricks compute stack")
        group.add_argument("--notebooks-only", action="store_true", help="Destroy only the notebooks stack")
        group.add_argument("--job-only", action="store_true", help="Destroy only the Databricks job stack")
        group.add_argument("--serving-only", action="store_true", help="Destroy only the model serving endpoint stack")
        args = parser.parse_args()

        repo_root = Path(__file__).resolve().parent.parent
        rg_dir = repo_root / "terraform" / "01_resource_group"
        databricks_dir = repo_root / "terraform" / "02_databricks_workspace"
        metastore_dir = repo_root / "terraform" / "03_uc_metastore_assignment"
        compute_dir = repo_root / "terraform" / "04_databricks_compute"
        notebooks_dir = repo_root / "terraform" / "05_notebooks"
        job_dir = repo_root / "terraform" / "06_job"
        serving_dir = repo_root / "terraform" / "07_model_serving_endpoint"

        try:
            workspace_url = get_output(databricks_dir, "databricks_workspace_url")
        except subprocess.CalledProcessError:
            workspace_url = None

        try:
            rg_name = get_output(rg_dir, "resource_group_name")
        except subprocess.CalledProcessError:
            rg_name = None

        if args.rg_only:
            tf_dirs = [rg_dir]
        elif args.databricks_only:
            tf_dirs = [databricks_dir]
        elif args.metastore_only:
            tf_dirs = [metastore_dir]
        elif args.compute_only:
            tf_dirs = [compute_dir]
        elif args.notebooks_only:
            tf_dirs = [notebooks_dir]
        elif args.job_only:
            tf_dirs = [job_dir]
        elif args.serving_only:
            tf_dirs = [serving_dir]
        else:
            tf_dirs = [
                serving_dir,
                job_dir,
                notebooks_dir,
                compute_dir,
                metastore_dir,
                databricks_dir,
                rg_dir,
            ]

        if workspace_url and (args.notebooks_only or notebooks_dir in tf_dirs):
            cleanup_workspace_files(workspace_url)

        if rg_name is not None:
            ensure_rg_tfvars(notebooks_dir, rg_name)
            ensure_rg_tfvars(job_dir, rg_name)
            ensure_rg_tfvars(serving_dir, rg_name)

        for tf_dir in tf_dirs:
            if not tf_dir.exists():
                raise FileNotFoundError(f"Missing Terraform dir: {tf_dir}")
            run(["terraform", f"-chdir={tf_dir}", "destroy", "-auto-approve"])
    except subprocess.CalledProcessError as exc:
        print(f"Command failed: {exc}")
        sys.exit(exc.returncode)
