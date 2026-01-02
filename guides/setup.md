# Project Setup Guide

This project provisions Azure Databricks resources for running the GenAI agent notebook, including Unity Catalog assignment and a compute cluster with preinstalled libraries.

## Prerequisites
- Azure CLI (az) installed and authenticated
- Terraform installed (>= 1.5)
- Python (for running the helper scripts)

## Terraform Setup
Check if Terraform is installed and on PATH:

```powershell
terraform version
```

If you need to install or update Terraform on Windows, use one of these:

```powershell
winget install HashiCorp.Terraform
```

```powershell
choco install terraform -y
```

After installing, re-open PowerShell and re-run terraform version.

## Azure CLI
Check your Azure CLI and login status:

```powershell
az --version
az login
az account show
```

## Project Structure
- terraform/01_resource_group: Azure resource group
- terraform/02_databricks_workspace: Azure Databricks workspace
- terraform/03_uc_metastore_assignment: Unity Catalog metastore assignment
- terraform/04_databricks_compute: Databricks cluster + preinstalled libraries
- terraform/05_notebooks: Databricks workspace notebooks
- terraform/06_job: Databricks job to run the driver notebook on the cluster
- terraform/07_model_serving_endpoint: Model serving endpoint (UC model)
- scripts/: Helper scripts to deploy/destroy Terraform resources
- notebooks/: Driver notebook

## Configure Terraform
The deploy script writes terraform.tfvars files automatically.
If you want different defaults, edit DEFAULTS in scripts/deploy.py before running.

## Deploy Resources
From the repo root or scripts folder, run:

```powershell
python scripts\deploy.py
```

Optional flags:

```powershell
python scripts\deploy.py --rg-only
python scripts\deploy.py --databricks-only
python scripts\deploy.py --metastore-only
python scripts\deploy.py --compute-only
python scripts\deploy.py --notebooks-only
python scripts\deploy.py --job-only
python scripts\deploy.py --serving-only
```

## Run the Notebook
1) Open `/Shared/genai-agents/driver.ipynb` to test, evaluate, register, and deploy the agent.
2) Or run the `GenAI Agents Driver Job` workflow to execute on the cluster.
3) After registering the model, run `python scripts/deploy.py --serving-only` to create the serving endpoint.
4) If you need custom concurrency settings, adjust them in the Serving UI after the endpoint is created.

## Destroy Resources
To tear down resources:

```powershell
python scripts\destroy.py
```

Optional flags:

```powershell
python scripts\destroy.py --rg-only
python scripts\destroy.py --databricks-only
python scripts\destroy.py --metastore-only
python scripts\destroy.py --compute-only
python scripts\destroy.py --notebooks-only
python scripts\destroy.py --job-only
python scripts\destroy.py --serving-only
```

## Notes
- Resource names are built from prefixes plus a random pet name by default. Override variables if needed.
- Unity Catalog assignment requires the Databricks account ID and metastore ID to match the workspace region.
- The metastore assignment step also grants the current Databricks user `USE CATALOG`, `CREATE SCHEMA`, `USE SCHEMA`, and `CREATE MODEL` on the workspace catalog (workspace name with hyphens replaced by underscores by default).
- The notebook uses the serving endpoint name configured inside `notebooks/driver.ipynb`.
- The compute stack defaults to SINGLE_USER and auto-resolves the current Databricks user email if `single_user_name` is not provided.
