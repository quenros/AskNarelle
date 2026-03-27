# AskNarelle: Intelligent Knowledge Base Management System 🎓🤖

AskNarelle is an intelligent Knowledge Base Management System designed
for educational settings. It transforms passive course content such as
lecture videos and documents into an interactive, queryable knowledge
base using Azure Cognitive Services and Large Language Models (LLMs).

------------------------------------------------------------------------

## 📑 Table of Contents

-   Project Overview
-   Prerequisites
-   Azure Services Configuration
-   Infrastructure Setup
-   Automated Setup (Terraform)
-   Manual Setup
-   Database Setup
-   Local Development Guide
-   Deployment Guide
-   Useful Resources
-   Notes

------------------------------------------------------------------------

## 📘 Project Overview

AskNarelle converts course materials into an intelligent knowledge base
using:

-   Azure OpenAI
-   Azure AI Search
-   Azure Cosmos DB (MongoDB vCore)
-   Azure Video Indexer

Features: 
- Course management 
- Document and video upload 
- Automatic knowledge extraction 
- AI-powered chat with course materials

------------------------------------------------------------------------

## 📋 Prerequisites

Install the following:

-   Node.js (v18 or v20)
-   Python (v3.12 recommended)
-   Terraform (\>=1.0)
-   Azure CLI
-   Docker
-   MongoDB Compass
-   Git (recommended)
-   VS Code (recommended)

------------------------------------------------------------------------

## ☁️ Azure Services Configuration

You can either:

1.  Deploy automatically using Terraform (recommended)
2.  Create resources manually via Azure Portal

⚠️ Azure OpenAI usually requires **Pay-As-You-Go subscription** and
approval.

------------------------------------------------------------------------

## Infrastructure Setup

## ⚙️ Automated Setup (Terraform)
## It is recommended that you set up with terraform because terraform will populate the .env for you too.

------------------------------------------------------------------------

## 📄 Terraform Variables

Some setups have prepopulated naming. Change only if the name is no longer unique/not usuable. You can find them under:

    terraform.tfvars

Example variables: 
- resource_group_name 
- location 
- storage_account_name

------------------------------------------------------------------------

Login first:

``` bash
az login
```

Initialize Terraform:

``` bash
terraform init
```

Apply infrastructure:

``` bash
terraform apply
```

After deployment Terraform generates:

    backend/.env

TAKE NOTE: This terraform script does NOT provision CosmosDB vCore. You have to do that manually.
------------------------------------------------------------------------

## 🛠 Manual Setup (Azure Portal)

### Resource Group

Example:

    asknarelle-rg

------------------------------------------------------------------------

### Storage Account

Create **General Purpose v2** storage.

Recommended: - Standard - LRS

------------------------------------------------------------------------

### Azure OpenAI

Deploy:

  Model                    Purpose
  ------------------------ ------------
  text-embedding-ada-002   embeddings
  gpt-4o-mini              chat

------------------------------------------------------------------------

### Azure AI Search

Used for document indexing and keyword search.

------------------------------------------------------------------------

### Azure Video Indexer

Link to storage and assign role:

    Storage Blob Data Contributor

------------------------------------------------------------------------

### Azure Container Registry

Tier:

    Basic

------------------------------------------------------------------------

### App Service Plan & Web App

Linux plan (B1 or higher).

Configure Web App to run Docker containers.

------------------------------------------------------------------------

### MongoDB Compass

To view your MongoDB locally, you can also download and install MongoDB Compass from the official MongoDB website.

In MongoDB Compass, copy and paste your MONGO_URI when you add new connection.

------------------------------------------------------------------------

### Azure OpenAI Setup

Once you create our Azure OpenAI resource, you need to create a model. 

Go to: https://ai.azure.com, "Deployments"

Deploy 2 models:
1) text-embedding-ada-002
2) gpt-4o-mini
 
If gpt-4o-mini does not exist anymore, deploy another GPT model and update your .env

------------------------------------------------------------------------------------------
## Database Setup (CosmosDB VCore)

Create a vCore cluster.

    Log in to the Azure Portal.

    In the top search bar, type Azure Cosmos DB and select it.

    Click + Create at the top left.

    On the "Select API option" page, find the Azure Cosmos DB for MongoDB tile and click Create.

    CRITICAL STEP: You will be prompted to choose a resource type. You must select vCore cluster (do not select Request Unit/RU).

    Under the Basics tab:

        Subscription: Select your active subscription.

        Resource Group: Select asknarelle (this should match the one Terraform creates).

        Cluster Name: Enter a unique name (e.g., asknarelle-db).

        Location: Choose a region close to your other resources (e.g., Japan West).

        Administrator credentials: Enter a secure username and password. Save these! You will need them for your connection string.

    Under the Cluster tier section, select the M30 tier (this is the most cost-effective tier that supports vector search).

    Click Next: Networking.

        Under "Firewall rules", select Allow public access from any Azure service within Azure to this cluster.

        Click + Add current client IP address so you can access it locally from MongoDB Compass.

        (Optional: If you want zero friction during local testing, add a rule with Start IP 0.0.0.0 and End IP 255.255.255.255, but be aware this opens the database to the internet).

    Click Review + create, and then Create.

    Once deployment is complete, go to the resource, click Connection strings on the left menu, and copy the string provided.

    Paste this connection string directly into the MONGO_URI field in your flask-server/.env file.

-----------------------------------------------------------------------------------------------------

------------------------------------------------------------------------------------------
## Video Indexer IAM Config

You need to assign a role to your Web App's managed identity on the Video Indexer resource. In the Azure Portal:

Go to your Video Indexer resource (asknarelle-video-indexer)
Click Access control (IAM) in the left sidebar
Click + Add → Add role assignment
Select the role Contributor (or a more specific role if available)
Click Next, then choose Managed identity
Click + Select members
Filter by App Service, then select asknarelle-portal
Click Select → Review + assign

This allows ur web app to upload videos to video indexer later.
-----------------------------------------------------------------------------------------------------


## 🗄 Database Initialization

Download and use MongoDB Compass and connect to CosmosDB. 

Copy and paste your Mongo Connection String into MongoDB Compass

### file_database

Collections: 
- courses 
- uploaded_files 
- activity_log

------------------------------------------------------------------------

### chathistory-storage

Collections: 
- conversations

------------------------------------------------------------------------

### videoindexer

Collections: 
- prompt_content_clean 
- video 
- course

Backend automatically creates **vector indexes** on first run.

------------------------------------------------------------------------

## Local Development Guide

## Environment Variables

File:

    flask-server/.env

Contains: - Mongo URI - Azure OpenAI keys - Azure Search keys - Video
Indexer credentials

------------------------------------------------------------------------

## Frontend Setup

``` bash
cd admin-app
npm install
npm run dev
```

Runs on:

    localhost:3000

------------------------------------------------------------------------

## Backend Setup

``` bash
cd flask-server
```

Create environment:

``` bash
python -m venv .venv
.venv\Scripts\activate
```

Install dependencies:

``` bash
pip install -r requirements.txt
```

Run server:

``` bash
flask run --host 0.0.0.0 --port 5000
```

Runs on:

    localhost:5000

------------------------------------------------------------------------

## Deployment Guide

Before deployment, 
1) You should be able to launch and use your application, if not, you will be deploying a non-working application.
2) Ensure that you have set up the authConfig.ts in the frontend folder correctly.

Frontend Authentication Configuration (MSAL):

Step 1: Register the Application

    Log in to the Azure Portal.

    Search for and select Microsoft Entra ID.

    In the left-hand menu, click App registrations, then select New registration.

    Give your app a name (e.g., "AskNarelle-Frontend").

    Under Supported account types, choose "Accounts in this organizational directory only" (Single tenant).

    Click Register.

Step 2: Get the Client ID and Tenant ID
Once your app is registered, you will be taken to its Overview page.

    clientId: Look for the value labeled Application (client) ID. Copy this and paste it into your msalConfig.

    authority: Look for the value labeled Directory (tenant) ID. Copy this ID and append it to the Microsoft login URL to create your authority string: https://login.microsoftonline.com/<YOUR_TENANT_ID>.

Step 3: Configure the Redirect URI

    From your app's page, click on Authentication in the left-hand menu.

    Click Add a platform and select Single-page application (SPA) (since you are using React/Next.js).

    Under Redirect URIs, enter your local development URL: http://localhost:3000/.

    Once your app is deployed, return to this exact page and add your production Web App URL (e.g., https://asknarelle-portal.azurewebsites.net/)

Afterwards, you are ready to deploy the application. 

Deployment:

Login:

``` bash
az login
```

Build image:

``` bash
docker build -t asknarelleacr.azurecr.io/unified:latest -f Dockerfile.unified .
```

Push image:

``` bash
az acr login --name asknarelleacr
docker push asknarelleacr.azurecr.io/unified:latest
```

Restart app:

``` bash
az webapp restart --name asknarelle-portal --resource-group asknarelle
```

------------------------------------------------------------------------

## 📚 Useful Resources

-   MongoDB Compass
-   Azure Video Indexer Portal
-   Azure CLI Docs
-   Terraform Azure Provider Docs

------------------------------------------------------------------------

## ⚠️ Notes

-   Ensure `.env` variables are configured.
-   Run frontend and backend simultaneously.
-   Azure CLI must be authenticated.
-   Verify CORS if frontend cannot call backend.
