param location string = 'eastus2'
param image string
@secure()
param accessKey string
param modelAccountName string = 'ai-witcher-cm7jzkadzmih2'

resource registry 'Microsoft.ContainerRegistry/registries@2023-07-01' existing = {
  name: 'witchercm7jzkadzmih2'
}
resource environment 'Microsoft.App/managedEnvironments@2024-03-01' existing = {
  name: 'cae-witcher-test'
}
resource modelAccount 'Microsoft.CognitiveServices/accounts@2025-06-01' existing = {
  name: modelAccountName
}
resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-witcher-test'
  location: location
}
resource registryPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, identity.id, 'AcrPull')
  scope: registry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '7f951dda-4ed3-4680-a7ca-43fe172d538d')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}
resource inferenceAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(modelAccount.id, identity.id, 'OpenAIUser')
  scope: modelAccount
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd')
    principalId: identity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}
resource app 'Microsoft.App/containerApps@2024-03-01' = {
  name: 'witcher-test'
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${identity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: environment.id
    workloadProfileName: 'Consumption'
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [{ name: 'test-access', value: accessKey }]
      registries: [{ server: registry.properties.loginServer, identity: identity.id }]
    }
    template: {
      containers: [{
        name: 'web'
        image: image
        resources: { cpu: json('0.5'), memory: '1Gi' }
        env: [
          { name: 'MODEL_PROVIDER', value: 'foundry' }
          { name: 'FOUNDRY_ENDPOINT', value: 'https://${modelAccountName}.cognitiveservices.azure.com' }
          { name: 'FOUNDRY_MODEL', value: 'witcher-mini' }
          { name: 'AZURE_CLIENT_ID', value: identity.properties.clientId }
          { name: 'APP_ACCESS_KEY', secretRef: 'test-access' }
          { name: 'REQUIRE_ACCESS_KEY', value: 'true' }
          { name: 'RUN_TIMEOUT_SECONDS', value: '180' }
        ]
        probes: [
          { type: 'Liveness', httpGet: { path: '/api/health', port: 8000 }, initialDelaySeconds: 10, periodSeconds: 30 }
          { type: 'Readiness', httpGet: { path: '/api/health', port: 8000 }, initialDelaySeconds: 5, periodSeconds: 10 }
        ]
      }]
      scale: {
        minReplicas: 0
        maxReplicas: 1
        rules: [{ name: 'http', http: { metadata: { concurrentRequests: '1' } } }]
      }
    }
  }
  dependsOn: [registryPull, inferenceAccess]
}
output url string = 'https://${app.properties.configuration.ingress.fqdn}'
