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
  resolved_catalog_name = var.catalog_name != null ? var.catalog_name : replace(
    data.terraform_remote_state.databricks.outputs.databricks_workspace_name,
    "-",
    "_"
  )
  resolved_model_name = "${local.resolved_catalog_name}.${var.schema_name}.${var.model_name}"
}

resource "databricks_model_serving" "endpoint" {
  name = var.endpoint_name

  config {
    served_models {
      name                 = var.served_model_name
      model_name           = local.resolved_model_name
      model_version        = var.model_version
      workload_size        = var.workload_size
      workload_type        = var.workload_type
      scale_to_zero_enabled = var.scale_to_zero_enabled
    }

    traffic_config {
      routes {
        served_model_name  = var.served_model_name
        traffic_percentage = 100
      }
    }
  }
}
