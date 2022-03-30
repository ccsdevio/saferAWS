'''
Please note: this lambda is designed to destroy infrastructure. I *strongly recommend* running just the monitoring tool for a while (a couple months if 
you're running a production environment for a business) before using this code
in anger. I have never pushed a line of code to production in my life, and you should have a commensurate level of trust in my code. Enjoy!
'''

import os
import boto3


def killall(region, home_region, logs):
    # just in case, check one more time to prevent from running in home_region:
    if region == home_region:
        logs['errors'].append({
            'usererror': 'killall was called in ' + region + ', which is set as home region. By design, killall will not run in home region'
        })
        print(logs)
        return {
            'statusCode': 405,
            'body': logs
        }

    logs[region] = {}
    logs[region]['ec2s'] = {}
    logs[region]['lambdas'] = {}
    logs[region]['users'] = {}
    logs[region]['db'] = {}
    logs[region]['alert'] = {}

    ec2_client = boto3.client('ec2', region_name=region)
    lambda_client = boto3.client('lambda', region_name=region)

    # EC2 section

    ec2Response = ec2_client.describe_instances()
    instances = []

    res = ec2Response['Reservations']

    if res:
        # Get the list of non-terminated instances
        for r in ec2Response['Reservations']:
            for i in r['Instances']:
                s = i['State']
                n = s['Name']
                if n != 'terminated':
                    instances.append(i['InstanceId'])

        if instances:
            logs[region]['ec2s'].update({'instances_found': instances})

            # Make sure that termination protection is off
            api_term_enabled = {}
            ec2s_terminated = {}
            for i in instances:
                ec2Response = ec2_client.modify_instance_attribute(
                    InstanceId=i,
                    DisableApiTermination={
                        'Value': False
                    })
                api_term_enabled.update(
                    {i: ec2Response['ResponseMetadata']['HTTPStatusCode']})
            logs[region]['ec2s'].update(
                {'api_termination_enabled': api_term_enabled})

            # Kill the instances
            ec2Response = ec2_client.terminate_instances(
                InstanceIds=instances,
            )
            for ti in ec2Response['TerminatingInstances']:
                ec2s_terminated.update(
                    {ti['InstanceId']: ti['CurrentState']['Name']})
            logs[region]['ec2s'].update(
                {'instances_terminated': ec2s_terminated})

        else:
            logs[region]['ec2s'].update(
                {'0_instances_terminated': 'only_terminated_found'})

    else:
        logs[region]['ec2s'].update({'0_instances_terminated': '0_found'})

    # Lambda section

    lambda_response = lambda_client.list_functions()
    functions_found = []
    functions_deleted = []

    if lambda_response['Functions']:

        # Get the list of Lambdas
        for l in lambda_response['Functions']:
            functions_found.append(l['FunctionName'])

        # Kill the lambdas
        logs[region]['lambdas'].update({'lambdas_found': functions_found})
        for f in functions_found:
            lambda_response = lambda_client.delete_function(
                FunctionName=f
            )
            functions_deleted.append(
                {f: lambda_response['ResponseMetadata']['HTTPStatusCode']})
            logs[region]['lambdas'].update(
                {'lambdas_deleted': functions_deleted})

    else:
        logs[region]['lambdas'].update(
            {'0_lambdas_terminated': 'no_lambdas_found'})

    # Delete all users' access keys and pwds
    iam_client = boto3.client('iam')
    users_found = []
    access_keys_found = 0
    access_keys_deleted = []
    users_list = iam_client.list_users()
    users = users_list['Users']
    for user in users:
        users_found.append(user['UserName'])

    for user in users_found:
        logs[region]['users'][user] = {}
        user_access_key_info = iam_client.list_access_keys(
            UserName=user
        )
        for ak in user_access_key_info['AccessKeyMetadata']:

            # If an access key exists for the user, delete it
            if ak['AccessKeyId']:
                access_keys_found += 1

                key_deleted_response = iam_client.delete_access_key(
                    UserName=user,
                    AccessKeyId=ak['AccessKeyId']
                )
                logs[region]['users'][user].update({'key_deleted_response_' + str(
                    access_keys_found): key_deleted_response['ResponseMetadata']['HTTPStatusCode']})
                access_keys_deleted.append(
                    key_deleted_response['ResponseMetadata']['HTTPStatusCode'])

            else:
                logs[region]['users'][user].update(
                    {'0_keys_deleted': '0_keys_found'})

            logs[region]['users'][user].update(
                {'access_keys_found': access_keys_found})
            logs[region]['users'][user].update(
                {'access_keys_deleted': len(access_keys_deleted)})

    return logs


def lambda_handler(event, context):

    logs = {}
    logs['errors'] = []

    # method will not run without a user-defined home_region
    try:
        home_region = os.environ['HOME_REGION']
    except KeyError:
        logs['errors'].append({
            'keyerror': 'env variable HOME_REGION must be set by user, to avoid deleting resources in home region'
        })
        print(logs)
        return {
            'statusCode': 405,
            'body': logs
        }

    region = event.get('region')

    # prevent from running in home_region:
    if region == home_region:
        logs['errors'].append({
            'usererror': 'killall was called in ' + region + ', which is set as home region. By design, killall will not run in home region'
        })
        print(logs)
        return {
            'statusCode': 405,
            'body': logs
        }
    else:

        logs = killall(region, home_region, logs)

        print(logs)

    return {
        'statusCode': 200,
        'body': logs
    }
