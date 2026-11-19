targetScope = 'subscription'

param location string
param resourceGroupName string = 'rg-witcher-test'

resource group 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: resourceGroupName
  location: location
  tags: {
    project: 'witcher-magentic'
    purpose: 'personal-testing'
  }
}

module hosting './hosting.bicep' = {
  name: 'witcher-hosting'
  scope: group
  params: {
    location: location
  }
}

output resourceGroupName string = group.name
output registryName string = hosting.outputs.registryName
output registryServer string = hosting.outputs.registryServer
output environmentName string = hosting.outputs.environmentName
output environmentId string = hosting.outputs.environmentId
