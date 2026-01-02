terraform {
  required_version = ">= 1.5"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.58"
    }
  }
}

provider "azurerm" {
  features {}
}

data "terraform_remote_state" "databricks" {
  backend = "local"
  config = {
    path = "../02_databricks_workspace/terraform.tfstate"
  }
}

data "terraform_remote_state" "compute" {
  backend = "local"
  config = {
    path = "../04_databricks_compute/terraform.tfstate"
  }
}

data "azurerm_databricks_workspace" "main" {
  name                = data.terraform_remote_state.databricks.outputs.databricks_workspace_name
  resource_group_name = var.resource_group_name
}

provider "databricks" {
  host                        = data.azurerm_databricks_workspace.main.workspace_url
  azure_workspace_resource_id = data.azurerm_databricks_workspace.main.id
  auth_type                   = "azure-cli"
}

locals {
  notebook_path = "${var.workspace_base_path}/${var.notebook_name}.ipynb"
}

resource "databricks_job" "driver" {
  name = var.job_name

  task {
    task_key            = "run_driver"
    existing_cluster_id = data.terraform_remote_state.compute.outputs.cluster_id

    notebook_task {
      notebook_path = local.notebook_path
    }
  }
}
