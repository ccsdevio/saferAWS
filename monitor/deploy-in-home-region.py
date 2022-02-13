import json
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
                    'AWS::Elasticsearch::Domain', 'AWS::IAM::Group', 'AWS::IAM::Policy', 'AWS::IAM::Role', 'AWS::IAM::User', 'AWS::ElasticLoadBalancingV2::LoadBalancer', 'AWS::ACM::Certificate', 'AWS::RDS::DBInstance', 'AWS::RDS::DBSubnetGroup', 'AWS::RDS::DBSecurityGroup', 'AWS::RDS::DBSnapshot', 'AWS::RDS::DBCluster', 'AWS::RDS::DBClusterSnapshot', 'AWS::RDS::EventSubscription', 'AWS::S3::Bucket', 'AWS::S3::AccountPublicAccessBlock', 'AWS::Redshift::Cluster', 'AWS::Redshift::ClusterSnapshot', 'AWS::Redshift::ClusterParameterGroup', 'AWS::Redshift::ClusterSecurityGroup', 'AWS::Redshift::ClusterSubnetGroup', 'AWS::Redshift::EventSubscription', 'AWS::SSM::ManagedInstanceInventory', 'AWS::CloudWatch::Alarm', 'AWS::CloudFormation::Stack', 'AWS::ElasticLoadBalancing::LoadBalancer', 'AWS::AutoScaling::AutoScalingGroup', 'AWS::AutoScaling::LaunchConfiguration', 'AWS::AutoScaling::ScalingPolicy', 'AWS::AutoScaling::ScheduledAction', 'AWS::DynamoDB::Table', 'AWS::CodeBuild::Project', 'AWS::WAF::RateBasedRule', 'AWS::WAF::Rule', 'AWS::WAF::RuleGroup', 'AWS::WAF::WebACL', 'AWS::WAFRegional::RateBasedRule', 'AWS::WAFRegional::Rule', 'AWS::WAFRegional::RuleGroup', 'AWS::WAFRegional::WebACL', 'AWS::CloudFront::Distribution', 'AWS::CloudFront::StreamingDistribution', 'AWS::Lambda::Function', 'AWS::NetworkFirewall::Firewall', 'AWS::NetworkFirewall::FirewallPolicy', 'AWS::NetworkFirewall::RuleGroup', 'AWS::ElasticBeanstalk::Application', 'AWS::ElasticBeanstalk::ApplicationVersion', 'AWS::ElasticBeanstalk::Environment', 'AWS::WAFv2::WebACL', 'AWS::WAFv2::RuleGroup', 'AWS::WAFv2::IPSet', 'AWS::WAFv2::RegexPatternSet', 'AWS::WAFv2::ManagedRuleSet', 'AWS::XRay::EncryptionConfig', 'AWS::SSM::AssociationCompliance', 'AWS::SSM::PatchCompliance', 'AWS::Shield::Protection', 'AWS::ShieldRegional::Protection', 'AWS::Config::ConformancePackCompliance', 'AWS::Config::ResourceCompliance', 'AWS::ApiGateway::Stage', 'AWS::ApiGateway::RestApi', 'AWS::ApiGatewayV2::Stage', 'AWS::ApiGatewayV2::Api', 'AWS::CodePipeline::Pipeline', 'AWS::ServiceCatalog::CloudFormationProvisionedProduct', 'AWS::ServiceCatalog::CloudFormationProduct', 'AWS::ServiceCatalog::Portfolio', 'AWS::SQS::Queue', 'AWS::KMS::Key', 'AWS::QLDB::Ledger', 'AWS::SecretsManager::Secret', 'AWS::SNS::Topic', 'AWS::SSM::FileData', 'AWS::Backup::BackupPlan', 'AWS::Backup::BackupSelection', 'AWS::Backup::BackupVault', 'AWS::Backup::RecoveryPoint', 'AWS::ECR::Repository', 'AWS::ECS::Cluster', 'AWS::ECS::Service', 'AWS::ECS::TaskDefinition', 'AWS::EFS::AccessPoint', 'AWS::EFS::FileSystem', 'AWS::EKS::Cluster', 'AWS::OpenSearch::Domain', 'AWS::EC2::TransitGateway', 'AWS::Kinesis::Stream', 'AWS::Kinesis::StreamConsumer', 'AWS::CodeDeploy::Application', 'AWS::CodeDeploy::DeploymentConfig', 'AWS::CodeDeploy::DeploymentGroup'
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
