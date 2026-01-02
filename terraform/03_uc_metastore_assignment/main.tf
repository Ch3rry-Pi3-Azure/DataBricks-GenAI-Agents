terraform {
  required_version = ">= 1.5"

  required_providers {
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.58"
    }
  }
}

data "terraform_remote_state" "databricks" {
  backend = "local"
  config = {
    path = "../02_databricks_workspace/terraform.tfstate"
  }
}

provider "databricks" {
  host       = "https://accounts.azuredatabricks.net"
  account_id = var.account_id
  auth_type  = "azure-cli"
}

provider "databricks" {
  alias                      = "workspace"
  host                       = data.terraform_remote_state.databricks.outputs.databricks_workspace_url
  azure_workspace_resource_id = data.terraform_remote_state.databricks.outputs.databricks_workspace_id
  auth_type                  = "azure-cli"
}

data "databricks_current_user" "me" {
  provider = databricks.workspace
}

locals {
  resolved_catalog_name = var.catalog_name != null ? var.catalog_name : replace(
    data.terraform_remote_state.databricks.outputs.databricks_workspace_name,
    "-",
    "_"
  )
}

resource "databricks_metastore_assignment" "main" {
  workspace_id         = var.workspace_id
  metastore_id         = var.metastore_id
}

resource "databricks_default_namespace_setting" "main" {
  provider = databricks.workspace

  namespace {
    value = var.default_catalog_name
  }
}

resource "databricks_grants" "catalog" {
  provider = databricks.workspace
  catalog  = local.resolved_catalog_name

  grant {
    principal  = data.databricks_current_user.me.user_name
    privileges = ["USE CATALOG", "CREATE SCHEMA"]
  }
}

resource "databricks_grants" "schema" {
  provider = databricks.workspace
  schema   = "${local.resolved_catalog_name}.${var.schema_name}"

  grant {
    principal  = data.databricks_current_user.me.user_name
    privileges = ["USE SCHEMA", "CREATE MODEL"]
  }
}
