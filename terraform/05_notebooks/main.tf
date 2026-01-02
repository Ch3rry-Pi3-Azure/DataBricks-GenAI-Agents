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
  notebooks = {
    "driver" = "${var.notebooks_dir}/driver.ipynb"
  }
}

resource "databricks_directory" "notebooks" {
  path = var.workspace_base_path
}

resource "databricks_notebook" "notebooks" {
  for_each = local.notebooks

  path           = "${var.workspace_base_path}/${each.key}.ipynb"
  format         = "JUPYTER"
  language       = "PYTHON"
  content_base64 = filebase64(each.value)
  depends_on     = [databricks_directory.notebooks]
}
