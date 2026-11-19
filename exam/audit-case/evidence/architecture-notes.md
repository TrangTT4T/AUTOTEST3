# QA platform v1 - how it works (team's notes, exam case)

- A Fargate **service** (DesiredCount 1) runs the regression suite in a loop, 24/7; the hourly
  pipeline also starts an extra task. Results go to the S3 bucket; the team opens reports by URL.
- Tasks run in a private subnet and reach the internet through one NAT gateway (one AZ).
- The suite uses the shop's **production** admin account (password in the task definition) to
  create test orders; orders are deleted by a nightly script "when it works".
- Mobile: Device Farm runs are started by hand from a laptop with the lead's personal access key.
- Flaky tests are retried 5 times inside the container; only the last attempt is reported.
- Nobody owns the AWS bill; the account has no budget alarm.
