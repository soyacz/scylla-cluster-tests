# Generate Billing Reports

This AWS lambda function uses Athena information to send billing usage information.

The lambda function uses email/password to send the billing information.
You need to set the following environment variables in your lambda function definition:

* SENDER
* PASSWORD
