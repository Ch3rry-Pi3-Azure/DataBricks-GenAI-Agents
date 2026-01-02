variable "resource_group_name" {
  type        = string
  description = "Name of the resource group containing the Databricks workspace"
}

variable "catalog_name" {
  type        = string
  description = "Catalog for the registered model (defaults to workspace name with hyphens replaced by underscores)"
  default     = null
}

variable "schema_name" {
  type        = string
  description = "Schema for the registered model"
  default     = "default"
}

variable "model_name" {
  type        = string
  description = "Registered model name in Unity Catalog"
  default     = "genai-agent"
}

variable "model_version" {
  type        = string
  description = "Model version to serve"
  default     = "1"
}

variable "endpoint_name" {
  type        = string
  description = "Serving endpoint name"
  default     = "genai-agent-endpoint"
}

variable "served_model_name" {
  type        = string
  description = "Name of the served model within the endpoint"
  default     = "genai-agent"
}

variable "workload_type" {
  type        = string
  description = "Workload type (CPU or GPU)"
  default     = "CPU"
}

variable "workload_size" {
  type        = string
  description = "Workload size (Small/Medium/Large)"
  default     = "Small"
}

variable "scale_to_zero_enabled" {
  type        = bool
  description = "Whether to scale the endpoint to zero when idle"
  default     = true
}
