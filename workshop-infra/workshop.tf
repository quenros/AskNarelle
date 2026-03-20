# ============================================
# PROVIDER CONFIGURATION
# ============================================
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 3.80.0" 
    }
    local = {
      source  = "hashicorp/local"
      version = "~> 2.0"
    }
  }
}

provider "azurerm" {
  features {}
  # FIX: Skip automatic provider registration since you don't have subscription-level access
  resource_provider_registrations = "none"
}

# Fetch current Azure client configuration 
data "azurerm_client_config" "current" {}

# ============================================
# 1. EXISTING RESOURCE GROUP (DATA FETCH)
# ============================================
# We use 'data' instead of 'resource' because the RG is already provisioned
data "azurerm_resource_group" "rg" {
  name = "260325-CDEFG-Workshop"
}

# ============================================
# 2. STORAGE ACCOUNT
# ============================================
resource "azurerm_storage_account" "storage" {
  name                     = var.storage_name
  resource_group_name      = data.azurerm_resource_group.rg.name
  location                 = var.storage_location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

# ============================================
# 3. AZURE OPENAI
# ============================================
resource "azurerm_cognitive_account" "openai" {
  name                = var.openai_name
  location            = var.openai_location
  resource_group_name = data.azurerm_resource_group.rg.name
  kind                = "OpenAI"
  sku_name            = "S0"

  custom_subdomain_name = var.openai_name 
}

# ============================================
# 4. APP SERVICE PLAN
# ============================================
resource "azurerm_service_plan" "asp" {
  name                = var.asp_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.asp_location
  os_type             = "Linux"
  sku_name            = "B1" 
}

# ============================================
# 5. APP SERVICE (WEB APP)
# ============================================
resource "azurerm_linux_web_app" "app" {
  name                = var.app_service_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.app_service_location
  service_plan_id     = azurerm_service_plan.asp.id

  site_config {
    application_stack {
      # FIX: Tell Azure to use your Docker image instead of raw Python
      docker_image_name   = "unified:latest"
      docker_registry_url = "https://${azurerm_container_registry.acr.login_server}"
    }
    
    container_registry_use_managed_identity = true
  }

  identity {
    type = "SystemAssigned"
  }

  app_settings = {
    # Helps Docker containers run smoother on App Service
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false" 
    
    # NOTE: If your Docker app listens on a specific port (like 5000 or 8000), 
    # remove the '#' below and update the number so Azure knows where to route traffic!
    # "WEBSITES_PORT" = "8000" 
  }
}

# ============================================
# 6. CONTAINER REGISTRY
# ============================================
resource "azurerm_container_registry" "acr" {
  name                = var.acr_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.acr_location
  sku                 = "Basic"
  admin_enabled       = true
}

# ============================================
# 7. VIDEO INDEXER (Deployed via ARM Template)
# ============================================
resource "azurerm_resource_group_template_deployment" "vi" {
  name                = "video-indexer-deployment"
  resource_group_name = data.azurerm_resource_group.rg.name
  deployment_mode     = "Incremental"

  template_content = <<TEMPLATE
{
  "$schema": "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#",
  "contentVersion": "1.0.0.0",
  "parameters": {
    "accountName": {
      "type": "string"
    },
    "location": {
      "type": "string"
    },
    "storageAccountId": {
      "type": "string"
    }
  },
  "resources": [
    {
      "type": "Microsoft.VideoIndexer/accounts",
      "apiVersion": "2024-01-01",
      "name": "[parameters('accountName')]",
      "location": "[parameters('location')]",
      "identity": {
        "type": "SystemAssigned"
      },
      "properties": {
        "storageServices": {
          "resourceId": "[parameters('storageAccountId')]"
        }
      }
    }
  ],
  "outputs": {
    "accountId": {
      "type": "string",
      "value": "[reference(resourceId('Microsoft.VideoIndexer/accounts', parameters('accountName')), '2024-01-01').accountId]"
    },
    "principalId": {
      "type": "string",
      "value": "[reference(resourceId('Microsoft.VideoIndexer/accounts', parameters('accountName')), '2024-01-01', 'Full').identity.principalId]"
    }
  }
}
TEMPLATE

  parameters_content = jsonencode({
    "accountName"      = { "value" = var.video_indexer_name },
    "location"         = { "value" = var.video_indexer_location },
    "storageAccountId" = { "value" = azurerm_storage_account.storage.id }
  })
}

# ============================================
# 8. SEARCH SERVICE
# ============================================
resource "azurerm_search_service" "search" {
  name                = var.search_name
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = var.search_location
  sku                 = "free"

  identity {
    type = "SystemAssigned"
  }
}

# ============================================
# 9. ROLE ASSIGNMENTS
# ============================================

# Video Indexer -> Storage Account permissions
resource "azurerm_role_assignment" "vi_storage_contributor" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = jsondecode(azurerm_resource_group_template_deployment.vi.output_content).principalId.value
}

resource "azurerm_role_assignment" "vi_contributor" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Contributor"
  principal_id         = jsondecode(azurerm_resource_group_template_deployment.vi.output_content).principalId.value
}

# AI Search -> Storage Account permissions (Allows AI Search to index Blobs)
resource "azurerm_role_assignment" "search_storage_reader" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Reader"
  principal_id         = azurerm_search_service.search.identity[0].principal_id
}

# Web App -> ACR permissions (Allows App Service to pull Docker Images securely)
resource "azurerm_role_assignment" "webapp_acr_pull" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_web_app.app.identity[0].principal_id
}

# Web App -> Storage Account permissions (Allows backend to securely manage blobs)
resource "azurerm_role_assignment" "webapp_storage_contributor" {
  scope                = azurerm_storage_account.storage.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_web_app.app.identity[0].principal_id
}

# ============================================
# 10. AUTO-GENERATE .ENV FILE
# ============================================
resource "local_file" "env_file" {
  filename = "${path.module}/flask-server/.env"
  
  content  = <<-EOT
AZURE_CONN_STRING="${azurerm_storage_account.storage.primary_connection_string}"
AZURE_STORAGE_KEY="${azurerm_storage_account.storage.primary_access_key}"
MONGO_URI=""
AZURE_OPENAI_API_KEY="${azurerm_cognitive_account.openai.primary_access_key}"
AZURE_OPENAI_DEPLOYMENT_NAME="gpt-4o-mini"
OPENAI_API_VERSION="2024-12-01-preview"
AZURE_OPENAI_ENDPOINT="${azurerm_cognitive_account.openai.endpoint}"
AZURE_COGNITIVE_SEARCH_API_KEY="${azurerm_search_service.search.primary_key}"
AZURE_COGNITIVE_SEARCH_ENDPOINT="https://${azurerm_search_service.search.name}.search.windows.net"

DB_NAME="videoindexer" 
API_VERSION="2025-04-01"
API_ENDPOINT="https://api.videoindexer.ai"
AZURE_RESOURCE_MANAGER="https://management.azure.com"

VIDEO_INDEXER_LOCATION="eastasia"
VIDEO_INDEXER_ACCOUNT_ID="${jsondecode(azurerm_resource_group_template_deployment.vi.output_content).accountId.value}"
VIDEO_INDEXER_ACCOUNT_NAME="${var.video_indexer_name}"
VIDEO_INDEXER_API_VERSION="2022-08-01"
VIDEO_INDEXER_API_KEY="" 
VIDEO_INDEXER_SUBSCRIPTION_ID="${data.azurerm_client_config.current.subscription_id}" 
VIDEO_INDEXER_RESOURCE_GROUP="${data.azurerm_resource_group.rg.name}"

EMBEDDING_MODEL="text-embedding-ada-002"

EOT
}