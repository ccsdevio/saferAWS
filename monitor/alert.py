import boto3
import os


def determine_alert(region, home_region):
    ddb_client = boto3.resource('dynamodb', region_name=home_region)
    table = ddb_client.Table('saferAWSAttackCounter')

    # currentCount = number of times we've alerted since last reset.
    query = {
        "ExpressionAttributeValues": {":q": 1},
        "Key": {"pk": "attackCount"},
        "UpdateExpression": "SET currentCount = currentCount + :q",
        "ReturnValues": "UPDATED_NEW"
    }
    response = table.update_item(**query)

    # if this is the first unauthorized activity, hit UADetected SNS topic.
    # if there has been more than one activity, hit UAContinued.
    if response['Attributes']['currentCount'] == 1:
        det_arn = f"arn:aws:sns:{os.environ['HOME_REGION']}:{os.environ['ACCOUNT']}:UnauthorizedActivityDetected"
        msg = "Unauthorized activity detected in " + region

        alert(det_arn, msg, home_region)

    else:
        cont_arn = f"arn:aws:sns:{os.environ['HOME_REGION']}:{os.environ['ACCOUNT']}:UnauthorizedActivityContinued"
        msg = "Multiple attacks detected in " + region

        alert(cont_arn, msg, home_region)

        # We're also going to reset the counter. If we're getting hammered, it won't
        # matter, and if not, this will keep us from forgetting:
        reset_counter(table)


def reset_counter(table):
    query = {
        "ExpressionAttributeValues": {":q": 0},
        "Key": {"pk": "attackCount"},
        "UpdateExpression": "SET currentCount = :q",
        "ReturnValues": "UPDATED_NEW"
    }
    table.update_item(**query)


def alert(arn, msg, home_region):
    sns_client = boto3.client('sns', region_name=home_region)
    snsMsg = {
        "TopicArn": arn,
        "Message": msg
    }
    response = sns_client.publish(**snsMsg)


def lambda_handler(event, context):

    # alert will not run without a user-defined home_region
    try:
        home_region = os.environ['HOME_REGION']
    except KeyError:
        print("env variable HOME_REGION must be set by user, to avoid alerting on activity in home region")
        return {
            'statusCode': 405,
            'body': 'env variable HOME_REGION must be set by user, to avoid alerting on activity in home region'
        }

    region = event.get('region')

    # prevent alert from running in home_region:
    if region == home_region:
        print(
            f"alert was called in {region}, which is set as home region. By design, alert will not run in home region")
        return {
            'statusCode': 405,
            'body': f"alert was called in {region}, which is set as home region. By design, alert will not run in home region"
        }
    else:

        determine_alert(region, home_region)

    return {
        'statusCode': 200,
        'body': 'alert executed successfully'
    }
