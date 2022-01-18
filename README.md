# saferAWS

An always-free AWS stack for personal accounts that monitors unused regions for unauthorized EC2 or Lambda creation. Upon detection, 
it first mitigates: deletes all functions and instances, and deletes all users' AWS keys. If more unauthorized use is
detected, it mitigates again and alerts the user through PagerDuty.
