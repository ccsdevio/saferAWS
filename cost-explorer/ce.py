import boto3

client = boto3.client('ce')

response = client.get_cost_and_usage(
    TimePeriod={
        'Start': '2022-01-20',
        'End': '2022-01-21'
    },
    Granularity='DAILY',
    Metrics=['UnblendedCost'],
    GroupBy=[
        {
            'Type': 'DIMENSION',
            'Key': 'SERVICE'
        }
    ]
)

print(response)
