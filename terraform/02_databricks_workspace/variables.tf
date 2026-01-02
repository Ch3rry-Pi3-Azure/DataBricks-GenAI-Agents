variable "resource_group_name" {
  type        = string
  description = "Name of the existing resource group"
}

variable "location" {
  type        = string
  description = "Azure region for the Databricks workspace (defaults to RG location if null)"
  default     = null
}

variable "workspace_name" {
  type        = string
  description = "Name of the Databricks workspace. If null, a random suffix is appended."
  default     = null
}

variable "workspace_name_prefix" {
  type        = string
  description = "Prefix used to build the Databricks workspace name when workspace_name is null"
  default     = "adb-genai"
}

variable "sku" {
  type        = string
  description = "Databricks SKU (standard or premium)"
  default     = "premium"
}

variable "managed_resource_group_name" {
  type        = string
  description = "Optional managed resource group name for Databricks"
  default     = null
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to the Databricks workspace"
  default     = {}
}
