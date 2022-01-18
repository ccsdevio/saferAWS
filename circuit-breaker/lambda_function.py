import json
import boto3
import os

apigateway_client = boto3.client('apigateway')

resources = []
responses = []


def tripBreaker():
    resp_args = {
        'restApiId': os.environ['REST_API_ID'],
    }
    response = apigateway_client.get_resources(**resp_args)
    items = response['items']

    for item in items:
        if item['path'] != '/':
            resources.append(item['id'])
    if resources:
        for resource in resources:
            res_args = {
                'restApiId': os.environ['REST_API_ID'],
                'resourceId': resource
            }
            response = apigateway_client.delete_resource(**res_args)
            # responses.append(response['ResponseMetadata']['HTTPStatusCode'])
            print("Resource:", resource, "Response:",
                  response['ResponseMetadata']['HTTPStatusCode'])
    else:
        print("No resources to delete")


def lambda_handler(event, context):
    tripBreaker()
    return {
        'statusCode': 200,
        'body': json.dumps('Successful run, see logs for details')
    }
