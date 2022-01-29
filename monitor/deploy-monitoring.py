import json
import botocore
import boto3
import os

config_client = boto3.client('config')

iam_client = boto3.client('iam')
s3_client = boto3.client('s3')
ec2_client = boto3.client('ec2')
logs = {}
logs['errors'] = []


def deploy_logs(region):
    logs[region] = {'region_name': region}
    logs[region]['http_codes'] = {}

    # Creates the log group needed for logging if it doesn't already exist
    logs[region]['logs'] = {}
    logs[region]['logs']['log_group'] = {}
    logs_client = boto3.client('logs', region_name=region)
    lg_list = logs_client.describe_log_groups()
    lg_names = []
    resource_arn = 'arn:aws:logs:' + region + ':' + \
        os.environ['ACCOUNT'] + ':log-group:/aws/events/*:*'
    policy_doc = '''{
                    "Statement": [
                        {
                            "Action": [
                                "logs:CreateLogStream",
                                "logs:PutLogEvents"
                            ],
                            "Effect": "Allow",
                            "Principal": {
                                "Service": ["events.amazonaws.com", "delivery.logs.amazonaws.com"]
                            },
                            "Resource": '''
    policy_doc = policy_doc + '\"' + resource_arn + '\"' + ''',
                            "Sid": "TrustEventsToStoreLogEvent"
                        }
                    ],
                    "Version": "2012-10-17"
                }'''
    resource_policy_args = {
        'policyName': 'TrustEventsToStoreLogEvents',
        'policyDocument': policy_doc
    }
    lgs = lg_list['logGroups']
    for lg in lgs:
        lg_names.append(lg['logGroupName'])
    if '/aws/events/log-all-unauthorized-activity' in lg_names:
        print('yes')
        logs[region]['logs']['log_group'] = 'log_group_exists'
        describe_resource_policies = logs_client.describe_resource_policies()
        print(describe_resource_policies)
        logs[region]['logs']['log_resource_policy'] = ''
        for resource in describe_resource_policies['resourcePolicies']:
            if resource['policyName'] == 'TrustEventsToStoreLogEvents':
                logs[region]['logs']['log_resource_policy'] = 'log_resource_policy_exists'
        # We seem to be having issues here:
        if hasattr(logs[region]['logs'], 'log_resource_policy') == False:
            put_resource_policy_response = logs_client.put_resource_policy(
                **resource_policy_args)
            logs[region]['http_codes']['put_resource_policy_response'] = put_resource_policy_response['ResponseMetadata']['HTTPStatusCode']

    else:
        create_log_group_response = logs_client.create_log_group(
            logGroupName='/aws/events/log-all-unauthorized-activity'
        )
        logs[region]['http_codes']['create_log_group_response'] = create_log_group_response['ResponseMetadata']['HTTPStatusCode']

        put_resource_policy_response = logs_client.put_resource_policy(
            **resource_policy_args)
        logs[region]['http_codes']['put_resource_policy_response'] = put_resource_policy_response['ResponseMetadata']['HTTPStatusCode']

    return logs


def deploy_config(region, config_client):

    # Deploys config to monitor lambdas

    # Install the config recorder
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
    put_config_response = config_client.put_configuration_recorder(
        **config_args)
    logs[region]['http_codes']['put_config_response'] = put_config_response['ResponseMetadata']['HTTPStatusCode']

    # Install the delivery channel
    put_delivery_channel_response = config_client.put_delivery_channel(
        DeliveryChannel={
            'name': 'default',
            's3BucketName': 'config-bucket-502245549462',
            'configSnapshotDeliveryProperties': {
                'deliveryFrequency': 'TwentyFour_Hours'
            }
        }
    )
    logs[region]['http_codes']['put_delivery_channel_response'] = put_delivery_channel_response['ResponseMetadata']['HTTPStatusCode']

    # Start the config recorder
    put_config_recorder_response = config_client.start_configuration_recorder(
        ConfigurationRecorderName='config-recorder'
    )
    logs[region]['http_codes']['put_config_recorder_response'] = put_config_recorder_response['ResponseMetadata']['HTTPStatusCode']

    return logs


def deploy_eventbridge(region):

    # Deploys eventbridge rules and targets

    # Deploy the eventbridge EC2 rule
    eventbridge_client = boto3.client('events', region_name=region)
    EC2_rule_name = "unauthorized-EC2-" + region
    EC2_rule_args = {
        'Name': EC2_rule_name,
        'EventPattern': '''{
        "source": ["aws.ec2"],
        "detail-type": ["EC2 Instance State-change Notification"],
        "detail": {
        "state": ["running"]
            } 
        }'''
    }
    put_EC2_rule_response = eventbridge_client.put_rule(**EC2_rule_args)
    logs[region]['http_codes']['put_EC2_rule_response'] = put_EC2_rule_response['ResponseMetadata']['HTTPStatusCode']

    # Deploy the eventbridge EC2 targets
    log_arn = 'arn:aws:logs:' + region + \
        ':502245549462:log-group:/aws/events/log-all-unauthorized-activity'
    EC2_target_args = {
        'Rule': EC2_rule_name,
        'Targets': [{
            'Id': 'unauthorized-activity-rule',
            'Arn': 'arn:aws:events:us-east-1:502245549462:event-bus/unauthorized-activity',
            'RoleArn': 'arn:aws:iam::502245549462:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_2083104951'
        },
            {
            'Id': 'log-all-unauthorized-activity',
            'Arn': log_arn,
        }]
    }
    put_EC2_targets_response = eventbridge_client.put_targets(
        **EC2_target_args)
    logs[region]['http_codes']['put_EC2_targets_response'] = put_EC2_targets_response['ResponseMetadata']['HTTPStatusCode']

    # Deploy the eventbridge lambda rule
    lambda_rule_name = "unauthorized-lambda-" + region
    resource_name = "arn:aws:cloudwatch:" + region + ":" + \
        "502245549462:alarm:unauthorized-lambda-" + region
    lambda_rule_args = {
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
    put_lambda_rule_response = eventbridge_client.put_rule(**lambda_rule_args)
    logs[region]['http_codes']['put_lambda_rule_response'] = put_lambda_rule_response['ResponseMetadata']['HTTPStatusCode']

    # Deploy the eventbridge lambda targets
    lambda_target_args = {
        'Rule': lambda_rule_name,
        'Targets': [{
            'Id': 'unauthorized-activity-rule',
            'Arn': 'arn:aws:events:us-east-1:502245549462:event-bus/unauthorized-activity',
            'RoleArn': 'arn:aws:iam::502245549462:role/service-role/Amazon_EventBridge_Invoke_Event_Bus_2083104951'
        },
            {
            'Id': 'log-all-unauthorized-activity',
            'Arn': log_arn,
        }]
    }
    put_lambda_targets_response = eventbridge_client.put_targets(
        **lambda_target_args)
    logs[region]['http_codes']['put_lambda_targets_response'] = put_lambda_targets_response['ResponseMetadata']['HTTPStatusCode']

    return logs


def deploy_monitoring(region):

    # Deploy the cloudwatch log group:
    logs = deploy_logs(region)

    # Deploy the config recorder:
    logs[region]['config'] = {}

    config_client = boto3.client('config', region_name=region)
    config_list_response = config_client.describe_configuration_recorders()
    # If our recorder already exists, log it and do nothing
    if config_list_response['ConfigurationRecorders'] and config_list_response['ConfigurationRecorders'][0]['name'] == 'config-recorder':
        logs[region]['config']['existing_config_recorders'] = config_list_response['ConfigurationRecorders'][0]['name']
    # if there's an existing config recorder other than ours we delete it and deploy ours:
    elif config_list_response['ConfigurationRecorders']:
        delete_configuration_recorder_response = config_client.delete_configuration_recorder(
            ConfigurationRecorderName=config_list_response['ConfigurationRecorders'][0]['name']
        )
        logs[region]['config']['delete_configuration_recorder_response'] = delete_configuration_recorder_response
        logs = deploy_config(region, config_client)
    # if there's no existing recorder we deploy ours:
    else:
        logs = deploy_config(region, config_client)

    # Deploy eventbridge:
    deploy_eventbridge(region)

    # Set the success message, and change it to fail if any response codes for operations were not 2xx:
    logs[region].update({region + '-deploy': 'succeeded'})

    for msg in logs[region]['http_codes']:
        code = logs[region]['http_codes'][msg]
        if code < 200 or code > 299:
            logs[region][region + '-deploy'] = 'failed'
            print(logs[region])
            return logs[region]

    print(logs[region])
    return logs[region]


def lambda_handler(event, context):
    try:
        home_region = os.environ['HOME_REGION']
    except KeyError:
        logs['errors'].append({
            'keyerror': 'env variable HOME_REGION must be set, to avoid deleting resources in home region'
        })
        return {
            'statusCode': 405,
            'body': logs
        }

    # Get the list of all regions, excluding home region
    regions = []
    response = ec2_client.describe_regions(AllRegions=True)
    region_entries = response['Regions']
    for ind_region in region_entries:
        regions.append(ind_region['RegionName'])
    regions.remove(home_region)

    # Deploy in all regions but home region
    for region in regions:
        logs.update(deploy_monitoring(region))
        if logs[region][region + '-deploy'] == 'failed':
            return {
                'statusCode': 405,
                'body': logs
            }

    print(logs)
    return {
        'statusCode': 200,
        'body': logs
    }
