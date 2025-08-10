export type AmplifyDependentResourcesAttributes = {
  "function": {
    "excelMapper": {
      "Name": "string",
      "Arn": "string",
      "Region": "string",
      "LambdaExecutionRole": "string"
    }
  },
  "api": {
    "excelMapperAPI": {
      "RootUrl": "string",
      "ApiName": "string",
      "ApiId": "string"
    }
  },
  "storage": {
    "excelMapperStorage": {
      "BucketName": "string",
      "Region": "string"
    }
  }
}