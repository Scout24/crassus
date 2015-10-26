# crassus
Cross Account Smart Software Update Service

## Deployer
### Event interface
Actual a SNS with a json payload is used to trigger crassus. The payload should look like this:

```json
      {
        "stackName": "sample-stack",
        "notificationARN": "<NOTIFICATION ARN>",
        "region": "<AWS-REGION-ID>",
        "params": {
          "dockerImageVersion": "69"
        }
      }
```


Sample event as expected from deployer
```json
{
  "Records": [
    {
      "EventVersion": "1.0",
      "EventSubscriptionArn": "<SUBSCRIPTION ARN>",
      "EventSource": "aws: sns",
      "Sns": {
        "SignatureVersion": "1",
        "Timestamp": "2015-10-23T11: 01: 16.140Z",
        "Signature": "<SIGNATURE>",
        "SigningCertUrl": "<SIGNING URL>",
        "MessageId": "<MESSAGE ID>",
        "Message": "{
        "stackName": "sample-stack",
        "notificationARN": "<NOTIFICATION ARN>",
        "region": "eu-west-1",
        "params": {
          "dockerImageVersion": "69"
        }
      }",
      "MessageAttributes": {
      },
      "Type": "Notification",
      "UnsubscribeUrl": "<UNSUBSCRIBE URL>",
      "TopicArn": "<TOPIC ARN>",
      "Subject": None
    }
  }
  ]
}
```