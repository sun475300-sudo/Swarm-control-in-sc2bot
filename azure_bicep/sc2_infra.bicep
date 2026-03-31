// SC2 Bot - Azure Bicep Infrastructure
// Resources: AKS cluster, Azure SQL, Storage Account, Container Registry

targetScope = 'resourceGroup'

// ========== Parameters ==========
@description('Environment name')
@allowed(['development', 'staging', 'production'])
param environment string = 'production'

@description('Azure region for all resources')
param location string = resourceGroup().location

@description('AKS node count')
@minValue(1)
@maxValue(20)
param aksNodeCount int = 3

@description('AKS node VM size')
param aksNodeVmSize string = 'Standard_D4s_v3'

@description('Azure SQL admin password')
@secure()
param sqlAdminPassword string

// ========== Variables ==========
var projectName = 'sc2bot'
var prefix      = '${projectName}-${environment}'
var tags        = { project: 'SC2Bot', environment: environment }

// ========== Network Module ==========
module network 'modules/network.bicep' = {
  name: 'network-deploy'
  params: {
    prefix:      prefix
    location:    location
    tags:        tags
  }
}

// ========== Compute Module (AKS) ==========
module compute 'modules/compute.bicep' = {
  name: 'compute-deploy'
  params: {
    prefix:       prefix
    location:     location
    tags:         tags
    subnetId:     network.outputs.aksSubnetId
    nodeCount:    aksNodeCount
    nodeVmSize:   aksNodeVmSize
  }
  dependsOn: [network]
}

// ========== Storage Module ==========
module storage 'modules/storage.bicep' = {
  name: 'storage-deploy'
  params: {
    prefix:   prefix
    location: location
    tags:     tags
  }
}

// ========== Azure Container Registry ==========
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: replace('${prefix}acr', '-', '')
  location: location
  sku: { name: 'Premium' }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
    zoneRedundancy: environment == 'production' ? 'Enabled' : 'Disabled'
  }
  tags: tags
}

// ========== Azure SQL Database ==========
resource sqlServer 'Microsoft.Sql/servers@2023-05-01-preview' = {
  name: '${prefix}-sql'
  location: location
  properties: {
    administratorLogin: 'sc2admin'
    administratorLoginPassword: sqlAdminPassword
    minimalTlsVersion: '1.2'
  }
  tags: tags
}

resource sqlDatabase 'Microsoft.Sql/servers/databases@2023-05-01-preview' = {
  parent: sqlServer
  name: 'sc2bot'
  location: location
  sku: {
    name: environment == 'production' ? 'GP_Gen5_4' : 'S2'
    tier: environment == 'production' ? 'GeneralPurpose' : 'Standard'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 107374182400  // 100GB
    zoneRedundant: environment == 'production'
    backupStorageRedundancy: 'Geo'
  }
  tags: tags
}

// ========== Outputs ==========
output aksClusterName string        = compute.outputs.aksClusterName
output acrLoginServer  string       = acr.properties.loginServer
output sqlServerFqdn   string       = sqlServer.properties.fullyQualifiedDomainName
output storageAccountName string    = storage.outputs.storageAccountName
output resourceGroupName string     = resourceGroup().name
