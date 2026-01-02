# Databricks GenAI Agents

Terraform-driven setup for an Azure Databricks workspace with Unity Catalog, compute with preinstalled packages, and notebook uploads.

## Quick Start
1) Install prerequisites:
   - Azure CLI (az)
   - Terraform (>= 1.5)
   - Python 3.10+

2) Authenticate to Azure:
```powershell
az login
az account show
```

3) Deploy infrastructure:
```powershell
python scripts\deploy.py
```

4) Open `/Shared/genai-agents/driver.ipynb` in Databricks.

5) Run the cells to test, evaluate, register, and deploy the agent.

## Project Structure
- terraform/01_resource_group: Azure resource group
- terraform/02_databricks_workspace: Azure Databricks workspace
- terraform/03_uc_metastore_assignment: Unity Catalog metastore assignment
- terraform/04_databricks_compute: Databricks cluster + preinstalled libraries
- terraform/05_notebooks: Databricks workspace notebooks
- terraform/06_job: Databricks job to run the driver notebook on the cluster
- terraform/07_model_serving_endpoint: Model serving endpoint (UC model)
- scripts/: Deploy/destroy helpers (auto-writes terraform.tfvars)
- guides/setup.md: Detailed setup guide
- notebooks/: Databricks notebook(s)

## Deploy/Destroy Options
Deploy specific stacks:
```powershell
python scripts\deploy.py --rg-only
python scripts\deploy.py --databricks-only
python scripts\deploy.py --metastore-only
python scripts\deploy.py --compute-only
python scripts\deploy.py --notebooks-only
python scripts\deploy.py --job-only
python scripts\deploy.py --serving-only
```

Destroy:
```powershell
python scripts\destroy.py
```

Destroy specific stacks:
```powershell
python scripts\destroy.py --rg-only
python scripts\destroy.py --databricks-only
python scripts\destroy.py --metastore-only
python scripts\destroy.py --compute-only
python scripts\destroy.py --notebooks-only
python scripts\destroy.py --job-only
python scripts\destroy.py --serving-only
```

## Guide
See guides/setup.md for detailed instructions.

## Notes
- The metastore assignment step grants the current Databricks user `USE CATALOG`, `CREATE SCHEMA`, `USE SCHEMA`, and `CREATE MODEL` on the workspace catalog (workspace name with hyphens replaced by underscores by default).
- Run `python scripts\deploy.py --serving-only` after registering the model in the notebook, since the endpoint needs the UC model to exist.
- The model serving Terraform resource exposes workload type/size and scale-to-zero; concurrency tuning may still need UI edits.
