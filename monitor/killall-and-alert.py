import json
import boto3
import os


# Note that DDB and SNS are in our home region (and IAM is global)
DDBClient = boto3.resource('dynamodb', region_name='us-east-1')
table = DDBClient.Table('saferAWSAttackCounter')
SNSClient = boto3.client('sns', region_name='us-east-1')
iam_client = boto3.client('iam')


def killall(region):

    ec2Client = boto3.client('ec2', region_name=region)
    lambdaClient = boto3.client('lambda', region_name=region)

    # EC2 section

    ec2Response = ec2Client.describe_instances()
    instances = []

    res = ec2Response['Reservations']

    # if res:
    #     # Get the list of non-terminated instances
    #     for r in ec2Response['Reservations']:
    #         for i in r['Instances']:
    #             s = i['State']
    #             n = s['Name']
    #             if n != 'terminated':
    #                 instances.append(i['InstanceId'])

    #     if instances:
    #         print("Instances found:\n", instances)

    #         # Make sure that termination protection is off.
    #         print("Disabling termination protection: ")
    #         for i in instances:
    #             ec2Response = ec2Client.modify_instance_attribute(
    #                 InstanceId=i,
    #                 DisableApiTermination={
    #                     'Value': False
    #                 })
    #             print(ec2Response['ResponseMetadata']['HTTPStatusCode'])

    #         # Kill the instances
    #         print("Terminating instances: ")
    #         ec2Response = ec2Client.terminate_instances(
    #             InstanceIds=instances,
    #         )
    #         print(ec2Response['TerminatingInstances'])
    #     else:
    #         print("Only terminated EC2s found.")

    # else:
    #     print("No EC2s found.")

    # Lambda section

    lambda_response = lambdaClient.list_functions()
    functions = []

    if lambda_response['Functions']:

        # Get the list of Lambdas
        for l in lambda_response['Functions']:
            functions.append(l['FunctionName'])

        # Delete all lambdas
        print("Lambdas found:\n", functions)
        print("Deleting all Lambda functions: ")
        for f in functions:
            lambda_response = lambdaClient.delete_function(
                FunctionName=f
            )
            print(
                f, ":", lambda_response['ResponseMetadata']['HTTPStatusCode'])

    else:
        print("No lambdas found.")

    # Delete all users' access keys and pwds
    access_keys = []
    users_list = iam_client.list_users()
    users = users_list['Users']
    for user in users:
        user_name = user['UserName']
        pwd = user['PasswordLastUsed']
        access_keys_list = iam_client.list_access_keys(
            UserName=user_name
        )
        print(access_keys_list)
        keys = access_keys_list['AccessKeyMetadata']
        if keys:
            for key in keys:
                access_key = key['AccessKeyId']
                iam_client.delete_access_key(
                    UserName=user_name,
                    AccessKeyId=access_key
                )
                print("Access key deleted:")
                print("User:", user_name)
                print("Key:", key)
        else:
            print("No access keys found for user", user_name)


def increment_counter_and_determine_alert(region):

    # increment counter
    query = {
        "ExpressionAttributeValues": {":q": 1},
        "Key": {"pk": "attackCount"},
        "UpdateExpression": "SET currentCount = currentCount + :q",
        "ReturnValues": "UPDATED_NEW"
    }
    response = table.update_item(**query)
    print("currentCount:", response['Attributes']['currentCount'])

    # if this is the first unauthorized activity, hit UADetected SNS topic.
    # if there has been more than one activity, hit UAContinued.
    if response['Attributes']['currentCount'] == 1:
        print("Alerting through UnauthorizedActivityDetected topic")
        det_arn = "arn:aws:sns:us-east-1:502245549462:UnauthorizedActivityDetected"
        msg = "Unauthorized activity detected in " + region
        alert(det_arn, msg)

    else:
        print("Multiple attacks detected. Alerting through UnauthorizedActivityContinued topic.")
        cont_arn = "arn:aws:sns:us-east-1:502245549462:UnauthorizedActivityContinued"
        msg = "Multiple attacks detected in " + region
        alert(cont_arn, msg)

        # We're also going to reset the counter. If we're getting hammered, it won't
        # matter, and if not, this will keep us from forgetting:
        reset_counter()


def reset_counter():
    query = {
        "ExpressionAttributeValues": {":q": 0},
        "Key": {"pk": "attackCount"},
        "UpdateExpression": "SET currentCount = :q",
        "ReturnValues": "UPDATED_NEW"
    }
    table.update_item(**query)


def alert(arn, msg):
    print(msg)
    snsMsg = {
        "TopicArn": arn,
        "Message": msg
    }
    response = SNSClient.publish(**snsMsg)


def lambda_handler(event, context):

    region = event.get('region')
    if region == 'us-east-1':
        print("Home region resources will not be deleted automatically.")
        print("To delete resources in home region, change code by hand.")

    else:
        killall(region)
        increment_counter_and_determine_alert(region)
    return {
        'statusCode': 200,
        'body': json.dumps('killall-and-alert ran successfully, see logs for details.')
    }
