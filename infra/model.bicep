param location string = 'eastus2'
param accountName string = 'ai-witcher-cm7jzkadzmih2'
param deploymentName string = 'witcher-mini'

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: accountName
    disableLocalAuth: true
    publicNetworkAccess: 'Enabled'
  }
}

// GlobalStandard is metered inference, not provisioned GPU/PTU capacity.
resource model 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = {
  parent: account
  name: deploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: 100
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2025-04-14'
    }
    versionUpgradeOption: 'OnceCurrentVersionExpired'
  }
}

output accountName string = account.name
output endpoint string = 'https://${accountName}.cognitiveservices.azure.com'
output deploymentName string = model.name
