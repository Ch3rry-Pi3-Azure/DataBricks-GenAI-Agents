output "databricks_workspace_id" {
  value = azurerm_databricks_workspace.main.id
}

output "databricks_workspace_name" {
  value = azurerm_databricks_workspace.main.name
}

output "databricks_workspace_url" {
  value = azurerm_databricks_workspace.main.workspace_url
}
