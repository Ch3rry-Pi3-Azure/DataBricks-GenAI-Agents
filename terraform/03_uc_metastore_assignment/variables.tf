variable "account_id" {
  type        = string
  description = "Databricks account ID (Azure Databricks account)"
}

variable "metastore_id" {
  type        = string
  description = "Unity Catalog metastore ID to assign to the workspace"
}

variable "workspace_id" {
  type        = number
  description = "Databricks workspace ID for metastore assignment"
}

variable "default_catalog_name" {
  type        = string
  description = "Default catalog name after metastore assignment"
  default     = "main"
}

variable "catalog_name" {
  type        = string
  description = "Catalog to grant UC permissions on (defaults to workspace name with hyphens replaced by underscores)"
  default     = null
}

variable "schema_name" {
  type        = string
  description = "Schema to grant UC permissions on"
  default     = "default"
}
