# ============================================
# RESOURCE GROUP
# ============================================
variable "rg_name" {
  description = "Name of the resource group"
  type        = string
}

variable "rg_location" {
  description = "Location of the resource group"
  type        = string
}

# ============================================
# STORAGE ACCOUNT
# ============================================
variable "storage_name" {
  description = "Name of the Storage Account"
  type        = string
}

variable "storage_location" {
  description = "Location of the Storage Account"
  type        = string
}

# ============================================
# AZURE OPENAI
# ============================================
variable "openai_name" {
  description = "Name of the Azure OpenAI account"
  type        = string
}

variable "openai_location" {
  description = "Location of the Azure OpenAI account"
  type        = string
}

# ============================================
# APP SERVICE PLAN & WEB APP
# ============================================
variable "asp_name" {
  description = "Name of the App Service Plan"
  type        = string
}

variable "asp_location" {
  description = "Location of the App Service Plan"
  type        = string
}

variable "app_service_name" {
  description = "Name of the App Service (Web App)"
  type        = string
}

variable "app_service_location" {
  description = "Location of the App Service"
  type        = string
}

# ============================================
# VIDEO INDEXER
# ============================================
variable "video_indexer_name" {
  description = "Name of the Video Indexer account"
  type        = string
}

variable "video_indexer_location" {
  description = "Location of the Video Indexer account"
  type        = string
}

# ============================================
# CONTAINER REGISTRY
# ============================================
variable "acr_name" {
  description = "Name of the Container Registry"
  type        = string
}

variable "acr_location" {
  description = "Location of the Container Registry"
  type        = string
}

# ============================================
# SEARCH SERVICE
# ============================================
variable "search_name" {
  description = "Name of the Azure AI Search Service"
  type        = string
}

variable "search_location" {
  description = "Location of the Search Service"
  type        = string
}