param location string
var suffix = uniqueString(subscription().subscriptionId, resourceGroup().name)

// Private image storage: admin passwords and anonymous pulls are disabled.
resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: 'witcher${suffix}'
  location: location
  sku: {
    name: 'Basic'
  }
  tags: {
    project: 'witcher-magentic'
  }
  properties: {
    adminUserEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

// Consumption only: no dedicated worker nodes or GPU allocation.
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: 'cae-witcher-test'
  location: location
  tags: {
    project: 'witcher-magentic'
  }
  properties: {
    zoneRedundant: false
    workloadProfiles: [
      {
        name: 'Consumption'
        workloadProfileType: 'Consumption'
      }
    ]
  }
}

output registryName string = registry.name
output registryServer string = registry.properties.loginServer
output environmentName string = environment.name
output environmentId string = environment.id
