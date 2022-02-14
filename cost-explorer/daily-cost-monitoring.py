'''
Daily cost monitoring. This lambda gets yesterday's
total AWS account costs, and if the total costs are 
greater than the env var COST_LIMIT, alerts via pagerduty
to ALERT_TOPIC_.

'''

import json
import os
import boto3
import datetime
from datetime import date
from pprint import pprint

ce_client = boto3.client('ce')
sns_client = boto3.client('sns')


def get_costs(earlier_date, later_date):
    ce_response = ce_client.get_cost_and_usage(

        TimePeriod={
            'Start': str(earlier_date),
            'End': str(later_date)
        },
        Granularity='MONTHLY',
        Metrics=['UnblendedCost']
        # Play with fields like this if you need a more detailed
        # presentation in your cost report (adding these fields may
        # break things below, specifically line 40)
        # GroupBy=[
        #     {
        #         'Type': 'DIMENSION',
        #         'Key': 'SERVICE'
        #     }
        # ]
    )

    return ce_response['ResultsByTime'][0]['Total']['UnblendedCost']['Amount']


def lambda_handler(event, context):
    today = date.today()
    print("today is", today)
    yesterday = today - datetime.timedelta(days=1)
    print("yesterday was", yesterday)

    yesterdays_costs = get_costs(yesterday, today)
    print(f"yesterdays_costs: {yesterdays_costs}")

    cost_report = {
        'cost report': {
            str(yesterday): yesterdays_costs
        }
    }

    if float(yesterdays_costs) > float(os.environ['COST_LIMIT']):
        '''Mitigation response goes here. By default this
        lambda publishes to an SNS topic, which I have configured 
        to hit PagerDuty. For personal accounts, consider
        automatic responses such as deleting or disabling resources 
        that you know would be the cause of these costs. You can
        automatically investigate by breaking the cost explorer response
        down by service; see commented code above.
        '''
        sns_response = sns_client.publish(
            TopicArn=os.environ['ALERT_TOPIC_ARN'],
            Message=f'Billing exceeded targets. {cost_report}',
            Subject='AWS BILLING ALERT'
        )
        print(f"sns_response: {sns_response}")

    return {
        'statusCode': 200,
        'body': json.dumps(cost_report)
    }
