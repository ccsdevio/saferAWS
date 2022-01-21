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


def deploy_monitoring(region):
    # Creates the log group needed for logging if it doesn't already exist
    lg_exists = False
    logs_client = boto3.client('logs', region_name=region)
    lg_list = logs_client.describe_log_groups()
    lgs = lg_list['logGroups']
    for lg in lgs:
        lg_exists = (lg['logGroupName'] == 'log-all-unauthorized-activity')
    if lg_exists == False:
        logs_client.create_log_group(
            logGroupName='log-all-unauthorized-activity'
        )

    # Deploys config to monitor lambdas
    config_client = boto3.client('config')

    config_response = config_client.describe_configuration_recorders()
    print(config_response)
    config_name = config_response['ConfigurationRecorders'][0]['name']
    print(config_name)

    delete_args = {'ConfigurationRecorderName': config_name}

    config_client.delete_configuration_recorder(**delete_args)

    config_args = {
        'ConfigurationRecorder': {
            'name': 'config-recorder',
            'roleARN': 'arn:aws:iam::502245549462:role/aws-service-role/config.amazonaws.com/AWSServiceRoleForConfig',
            'recordingGroup': {
                'allSupported': False,
                'resourceTypes': [
                    'AWS::Lambda::Function'
                ]
            }
        }
    }

    config_client.put_configuration_recorder(**config_args)

    config_client.put_delivery_channel(
        DeliveryChannel={
            'name': 'default',
            's3BucketName': 'config-bucket-502245549462',
            'configSnapshotDeliveryProperties': {
                'deliveryFrequency': 'TwentyFour_Hours'
            }
        }
    )

    config_client.start_configuration_recorder(
        ConfigurationRecorderName='config-recorder'
    )

    # Deploys the eventbridge EC2 rule

    eventbridge_client = boto3.client('events', region_name=region)

    EC2_rule_name = "unauthorized-EC2-" + region
    rule_args = {
        'Name': EC2_rule_name,
        'EventPattern': '''{
        "source": ["aws.ec2"],
        "detail-type": ["EC2 Instance State-change Notification"],
        "detail": {
        "state": ["running"]
            } 
        }'''
    }
    eventbridge_client.put_rule(**rule_args)

    # Deploys the eventbridge EC2 targets
    log_arn = 'arn:aws:logs:' + region + \
        ':502245549462:log-group:/aws/events/log-all-unauthorized-activity'
    target_args = {
        'Rule': EC2_rule_name,
        'Targets': [{
            'Id': 'unauthorized-activity-rule',
            'Arn': 'arn:aws:events:us-east-1:502245549462:event-bus/unauthorized-activity',
            'RoleArn': 'arn:aws:iam::502245549462:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_2083104951'
        },
            {
            'Id': 'log-all-unauthorized-activity',
            'Arn': log_arn
        }]
    }
    eventbridge_client.put_targets(**target_args)

    # Deploys the eventbridge lambda rule
    lambda_rule_name = "unauthorized-lambda-" + region
    resource_name = "arn:aws:cloudwatch:" + region + ":" + \
        "502245549462:alarm:unauthorized-lambda-" + region
    rule_args = {
        'Name': lambda_rule_name,
        'EventPattern': '''{
            "source": ["aws.config"],
            "detail": {
                "configurationItem": {
                    "configurationItemStatus": ["ResourceDiscovered"],
                    "resourceType": ["AWS::Lambda::Function"]
                }
            }
        }'''
    }
    eventbridge_client.put_rule(**rule_args)

    # Deploys the eventbridge lambda targets
    log_arn = 'arn:aws:logs:' + region + \
        ':502245549462:log-group:/aws/events/log-all-unauthorized-activity'
    target_args = {
        'Rule': lambda_rule_name,
        'Targets': [{
            'Id': 'unauthorized-activity-rule',
            'Arn': 'arn:aws:events:us-east-1:502245549462:event-bus/unauthorized-activity',
            'RoleArn': 'arn:aws:iam::502245549462:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_2083104951'
        },
            {
            'Id': 'log-all-unauthorized-activity',
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
