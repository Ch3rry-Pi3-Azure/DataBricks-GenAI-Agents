variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "notebooks_dir" {
  type        = string
  description = "Path to the local notebooks directory"
  default     = "../../notebooks"
}

variable "workspace_base_path" {
  type        = string
  description = "Destination folder in the Databricks workspace"
  default     = "/Shared/genai-agents"
}
