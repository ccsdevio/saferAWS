import json
import boto3

config_client = boto3.client('config')

iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
ec2_client = boto3.client('ec2')

home_region = 'us-east-1'

# Gets the list of all regions, excluding home region
regions = []
response = ec2_client.describe_regions(AllRegions=True)
region_entries = response['Regions']
for ind_region in region_entries:
    regions.append(ind_region['RegionName'])
regions.remove(home_region)

# Gets the policy documents for the needed roles from an s3 object
roles_doc = s3_client.get_object(
    Bucket='iam-policy-docs',
    Key='policy-docs.json'
)
roles = json.loads(roles_doc['Body'].read())


def deploy_monitoring(region):
    # Creates the log group needed for logging if it doesn't already exist
    lg_exists = False
    logs_client = boto3.client('logs', region_name=region)
    lg_list = logs_client.describe_log_groups()
    lgs = lg_list['logGroups']
    for lg in lgs:
        lg_exists = (lg['logGroupName'] == 'log-all')
    if lg_exists == False:
        logs_client.create_log_group(
            logGroupName='log-all'
        )

    # Deploys the eventbridge rules
    eventbridge_client = boto3.client('events', region_name=region)
    rule_name = "unauthorized-EC2-" + region
    rule_args = {
        'Name': rule_name,
        'EventPattern': '''{
        "source": ["aws.ec2"],
        "detail-type": ["EC2 Instance State-change Notification"],
        "detail": {
        "state": ["running"]
            } 
        }'''
    }
    eventbridge_client.put_rule(**rule_args)

    # Deploys the eventbridge targets
    log_arn = 'arn:aws:logs:' + region + ':502245549462:log-group:/aws/events/log-all'
    target_args = {
        'Rule': rule_name,
        'Targets': [{
            'Id': 'unauthorized-activity-rule',
            'Arn': 'arn:aws:events:us-east-1:502245549462:event-bus/unauthorized-activity',
            'RoleArn': 'arn:aws:iam::502245549462:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_2083104951'
        },
            {
            'Id': 'log-all',
            'Arn': log_arn
        }]
    }
    eventbridge_client.put_targets(**target_args)

    print("Deployed correctly in", region)


def lambda_handler(event, context):
    for region in regions:
        deploy_monitoring(region)
    return {
        'statusCode': 200,
        'body': json.dumps('Called deploy_monitoring for all regions, see logs for details')
    }
