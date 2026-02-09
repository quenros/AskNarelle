# 1. Provider Configuration
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# 2. Resource Group (Found 'asknarelle' in your CSV)
resource "azurerm_resource_group" "rg" {
  name     = "asknarelle"
  location = "Southeast Asia" 
}

# 3. Azure Cosmos DB (MongoDB) - From CSV: "asknarelle" (Japan West)
resource "azurerm_cosmosdb_account" "cosmos" {
  name                = "asknarelle"
  location            = "Japan West"
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "MongoDB"

  capabilities {
    name = "EnableMongo"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = "Japan West"
    failover_priority = 0
  }
}

# 4. Storage Account - From CSV: "asknarelle" (East Asia)
resource "azurerm_storage_account" "storage" {
  name                     = "asknarelle"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = "East Asia"
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# 5. Azure OpenAI - From CSV: "asknarelle-fyp" (Japan East)
resource "azurerm_cognitive_account" "openai" {
  name                = "asknarelle-fyp"
  location            = "Japan East"
  resource_group_name = azurerm_resource_group.rg.name
  kind                = "OpenAI"
  sku_name            = "S0"
}

# 6. App Service Plan (Required for App Service)
resource "azurerm_service_plan" "asp" {
  name                = "ASP-asknarelle-b5da" # Inferred from your App Service
  resource_group_name = azurerm_resource_group.rg.name
  location            = "Southeast Asia"
  os_type             = "Linux"
  sku_name            = "B1" # Change to "F1" (Free) or "B1" (Basic) as needed
}

# 7. App Service (Web App) - From CSV: "asknarelle-portal" (Southeast Asia)
resource "azurerm_linux_web_app" "app" {
  name                = "asknarelle-portal"
  resource_group_name = azurerm_resource_group.rg.name
  location            = "Southeast Asia"
  service_plan_id     = azurerm_service_plan.asp.id

  site_config {
    application_stack {
      python_version = "3.9" # Or your specific version
    }
  }
}

# 8. Video Indexer - From CSV: "asknarelle-video-indexer" (East Asia)
resource "azurerm_video_indexer_account" "vi" {
  name                = "asknarelle-video-indexer"
  location            = "East Asia"
  resource_group_name = azurerm_resource_group.rg.name
  storage_account_id  = azurerm_storage_account.storage.id

  identity {
    type = "SystemAssigned"
  }
}

# 9. Search Service - From CSV: "asknarellefree" (Central US)
resource "azurerm_search_service" "search" {
  name                = "asknarellefree"
  resource_group_name = azurerm_resource_group.rg.name
  location            = "Central US"
  sku                 = "free"
}

# PERMISSIONS
# Grants Video Indexer permission to access the Storage Account
resource "azurerm_role_assignment" "vi_storage_contributor" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_video_indexer_account.vi.identity[0].principal_id
}

resource "azurerm_role_assignment" "vi_contributor" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Contributor"
  principal_id         = azurerm_video_indexer_account.vi.identity[0].principal_id
}