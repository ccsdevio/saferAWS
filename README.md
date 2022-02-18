# saferAWS

Free AWS stacks to help prevent surprise AWS bills for personal projects. This project has three parts:

## monitor
An always-almost-free AWS stack for personal accounts that monitors unused regions for unauthorized EC2 or Lambda creation. Upon detection, it first mitigates: deletes all functions and instances, and deletes all users' AWS keys. If more unauthorized use is
detected, it mitigates again and alerts the user through PagerDuty.

## circuit-breaker
An always-free stack that monitors for unusual traffic spikes, and disconnects public access (the example deletes an API route) upon detection.

## cost-explorer
Daily cost monitoring. Set to publish to an SNS topic when yesterday's costs exceed a daily budget.
