variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "workspace_base_path" {
  type        = string
  description = "Workspace base path for notebooks"
  default     = "/Shared/genai-agents"
}

variable "notebook_name" {
  type        = string
  description = "Notebook filename without extension"
  default     = "driver"
}

variable "job_name" {
  type        = string
  description = "Display name for the Databricks job"
  default     = "GenAI Agents Driver Job"
}
