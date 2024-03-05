import json
import time
import boto3
from botocore.exceptions import ClientError
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import reduce
from datetime import date, timedelta
import os

DATABASE = 'reports'
TABLE = 'dialy_athens'
S3_OUTPUT = 's3://athens-reports/'
S3_OUTPUT = 's3://athens-reports/athen-report/dialy-athens/dialy-athens/'

SENDER = os.environ['SENDER']
PASSWORD = os.environ['PASSWORD']

QUERY = ("SELECT '%s' date, line_item_usage_account_id account, line_item_product_code Product, " +
         "FLOOR(sum(line_item_blended_cost)) cost FROM reports.dialy_athens " +
         "where year='%s' and month='%s' " +
         "AND identity_time_interval = '%s' " +
         "group by line_item_usage_account_id, line_item_product_code " +
         "HAVING sum(line_item_blended_cost) > 1 " +
         "order by line_item_usage_account_id, sum(line_item_blended_cost) DESC"
         )


ACCOUNTS = {'43400831220': 'DBAAS Sandbox',
            '696340704738': 'DBAAS Production',
            '734708892259': 'DBAAS LAB',
            '992070034275': 'DBBAS Staging',
            '797456418907': 'R&D',
            '403205517060': 'Solution'}

MAX_PER_ACCOUNTS = {'43400831220': 100,
                    '696340704738': 3500,
                    '734708892259': 300,
                    '992070034275': 100,
                    '797456418907': 300,
                    '403205517060': 100}

DBAAS_ACCOUNTS = ['43400831220', '696340704738', '734708892259', '992070034275']
RECIPIENTS = {"amnon@scylladb.com": DBAAS_ACCOUNTS + ['797456418907', '403205517060'],
              "shlomi@scylladb.com": DBAAS_ACCOUNTS + ['797456418907', '403205517060'],
              "noam@scylladb.com": DBAAS_ACCOUNTS,
              "dor@scylladb.com": DBAAS_ACCOUNTS + ['797456418907', '403205517060'],
              "karin@scylladb.com": DBAAS_ACCOUNTS + ['797456418907', '403205517060'],
              "eyal@scylladb.com": ['403205517060']
              }

RECIPIENTS = {
    'billing_43400831220@scylladb.com': ['43400831220'],
    'billing_696340704738@scylladb.com': ['696340704738'],
    'billing_734708892259@scylladb.com': ['734708892259'],
    'billing_992070034275@scylladb.com': ['992070034275'],
    'billing_797456418907@scylladb.com': ['797456418907'],
    'billing_403205517060@scylladb.com': ['403205517060']
}
# RECIPIENTS = {"amnon@scylladb.com" : DBAAS_ACCOUNTS + ['797456418907', '403205517060']}

# The HTML body of the email.

HTML = """
<html>
  <head>
  <style type="text/css">
        table {
            font-family:Gotham, "Helvetica Neue", Helvetica, Arial, "sans-serif";
            font-size: 14px;
            color: #333;
            padding: 20px;
            padding-top: 0px;
        }
        H1 {
            font-family:Gotham, "Helvetica Neue", Helvetica, Arial, "sans-serif";font-weight: 300;
            color: #6673d2;
        }
        H2 {
            font-family:Gotham, "Helvetica Neue", Helvetica, Arial, "sans-serif";font-weight: 400;
            font-size: 22px;
            color: #000;
            padding-left: 20px;
            margin-bottom: 5px;
            margin-top: 20px;
        }
        H3 {
            font-family:Gotham, "Helvetica Neue", Helvetica, Arial, "sans-serif";font-weight: 400;
            font-size: 15px;
            color: #000;
            padding-left: 20px;
            margin-bottom: 5px;
            margin-top: 20px;
        }
      </style>
  </head>
  <body>
  <h1>Amnon's Auto generated Report</h1>
  <h4>Version 0.5</h4>
This beta version of the daily billing reports are auto-generated.
<h2>Important Update</h2>
There is a known issue with billing information from the day before. That report does not contain
the total cost.
<br>
Until it can be resolved, each email will contain the information from the day before and the day before that.
<br>
The exceed limit warning will be given for either of the days.

<br>
<br>
Use the more info link for as a quick navigation link to AWS billing information.
<br>
<br>
%s
  </body>
</html>
"""

TABLE = """
<h2>Daily Usage For Account %s</h2>
<h3 %s>Total Daily cost %s</h3>
<a href="%s">More Info</a>
<br>
<br>
<table style="border: 1px solid black;">
<tr height="24px" style="background-color:#24b7ea;border:0px solid black;text-align:left;color: #FFFFFF;text-transform: capitalize;">
%s
</tr>
%s
</table>
"""

# number of retries
RETRY_COUNT = 30


def result_to_header(result):
    header = reduce((lambda a, b: a + b), ['<th style="padding-left: 4px;">' +
                    i['VarCharValue'] + '</th>' for i in result['Data']])
#    print(header)
    return header


def make_row(results):
    result = results['Data']
#    print("make_row")
#    print(results)
#    print(result)

    return '<tr height="32px">' + reduce((lambda a, b: a + b), ['<td style="padding-right: 30px;padding-left: 4px;">' + i['VarCharValue'] + '</td>' for i in result]) + '</tr>'


def result_to_table(result):
    #    print(result)
    table = reduce((lambda a, b: a + b), [make_row(i) for i in result])
    return table


def make_table(header, account, results_data):
    if results_data and results_data['res']:
        results = results_data['res']
        total = results_data['total']
        table = result_to_table(results)
        link_url = "https://console.aws.amazon.com/cost-reports/home?#/custom?groupBy=Service&hasBlended=false&hasAmortized=false&excludeDiscounts=true&excludeTaggedResources=false&excludeCategorizedResources=false&timeRangeOption=MonthToDate&granularity=Daily&reportName=&reportType=CostUsage&isTemplate=true&filter=%5B%7B%22dimension%22:%22LinkedAccount%22,%22values%22:%5B%22" + \
            account + "%22%5D,%22include%22:true,%22children%22:null%7D%5D&chartStyle=Group&forecastTimeRangeOption=None&usageAs=usageQuantity"

        style = ""
        if total > MAX_PER_ACCOUNTS[account]:
            total = str(total) + "$ That excceded the Daily limit of " + str(MAX_PER_ACCOUNTS[account]) + '$'
            style = 'style="color:red"'
        else:
            total = str(total) + "$ out of the " + str(MAX_PER_ACCOUNTS[account]) + '$ Daily limit.'
        return TABLE % (ACCOUNTS[account], style, total, link_url, header, table)
    return ""


def send_message(orgenized_result, yesterday_orgenized_result, recipient, accounts, dt, smtpserver):
    results_by_account = orgenized_result['results_by_account']
    yesterday_results_by_account = yesterday_orgenized_result['results_by_account']

    header = orgenized_result['header']
    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER
    msg['To'] = recipient
    exceed = None
    html = HTML
    account_name = ""
    for i in accounts:
        if i in results_by_account:
            if account_name == "":
                account_name = ACCOUNTS[i]
            if MAX_PER_ACCOUNTS[i] < results_by_account[i]['total']:
                exceed = True
    for i in accounts:
        if i in yesterday_results_by_account:
            if MAX_PER_ACCOUNTS[i] < yesterday_results_by_account[i]['total']:
                exceed = True
    if account_name == '':
        return
    if exceed:
        msg['Subject'] = "AWS Usage report " + dt + " " + account_name + " Limit Exceeded!"
    else:
        msg['Subject'] = "AWS Usage report " + dt + " " + account_name + " Daily Report"
    tables = reduce((lambda a, b: a + b), [make_table(header, i, results_by_account[i] if i in results_by_account else {}) for i in accounts] +
                    [make_table(header, i, yesterday_results_by_account[i]
                                if i in yesterday_results_by_account else {}) for i in accounts]
                    )
    part2 = MIMEText(html % (tables), 'html')
    # msg.attach(part1)
    msg.attach(part2)

    smtpserver.sendmail(SENDER, recipient, msg.as_string())


def orgenize_result(results):
    result = results['ResultSet']['Rows']
    orgenized_result = {}
    orgenized_result['header'] = result_to_header(result[0])
    result.pop(0)
    results_by_account = {}
    for r in result:
        account = r['Data'][1]['VarCharValue']
        if account not in results_by_account:
            results_by_account[account] = {}
            results_by_account[account]['res'] = []
            results_by_account[account]['total'] = 0
        results_by_account[account]['res'].append(r)
        results_by_account[account]['total'] = results_by_account[account]['total'] + \
            int(float(r['Data'][3]['VarCharValue']))
    orgenized_result['results_by_account'] = results_by_account
    return orgenized_result


def send_email(results, yesterday_result, dt):
    smtpserver = smtplib.SMTP("smtp.gmail.com", 587)
    smtpserver.ehlo()
    smtpserver.starttls()
    smtpserver.ehlo()
    smtpserver.login(SENDER, PASSWORD)
#    msg='Subject:\nThis Amnon\'s report from AWS'

    if 'ResultSet' in results and 'Rows' in results['ResultSet']:
        orgenized_result = orgenize_result(results)
        yesterday_orgenized_result = orgenize_result(yesterday_result)

        for recipient in RECIPIENTS:
            send_message(orgenized_result, yesterday_orgenized_result, recipient, RECIPIENTS[recipient], dt, smtpserver)
    smtpserver.close()


def get_athena_data(year, month, day1, day2):
    # query = "SELECT sum(line_item_blended_cost) FROM %s.%s where year='%s' and month='%s';" % (DATABASE, TABLE,  year, month)
    # CAST(line_item_usage_start_date as DATE),
    #  order by CAST(line_item_usage_start_date as DATE), line_item_usage_account_id
    # "AND line_item_usage_start_date between CURDATE() - INTERVAL 1 DAY AND CURDATE() " +
    #    "and line_item_line_item_type='Usage' and line_item_operation" +
    # "='RunInstances' and product_product_family='Compute Instance' " +
    day_range = year + '-' + month + '-' + day1 + 'T00:00:00Z/' + year + '-' + month + '-' + day2 + 'T00:00:00Z'
    date = year + '-' + month + '-' + day1
    query = QUERY % (date, year, month, day_range)
    # athena client
    print(query)
    client = boto3.client('athena')

    # Execution
    response = client.start_query_execution(
        QueryString=query,
        QueryExecutionContext={
            'Database': DATABASE
        },
        ResultConfiguration={
            'OutputLocation': S3_OUTPUT,
        }
    )
# get query execution id
    query_execution_id = response['QueryExecutionId']
    print(query_execution_id)

    # get execution status
    for i in range(1, 1 + RETRY_COUNT):

        # get query execution
        query_status = client.get_query_execution(QueryExecutionId=query_execution_id)
        query_execution_status = query_status['QueryExecution']['Status']['State']

        if query_execution_status == 'SUCCEEDED':
            print("STATUS:" + query_execution_status)
            break

        if query_execution_status == 'FAILED':
            raise Exception("STATUS:" + query_execution_status)

        else:
            print("STATUS:" + query_execution_status)
            time.sleep(i)
    else:
        client.stop_query_execution(QueryExecutionId=query_execution_id)
        raise Exception('TIME OVER')

    # get query results
    result = client.get_query_results(QueryExecutionId=query_execution_id)
    print(result)
    return result


def get_athen_data_by_date(day):
    yesterday = day - timedelta(days=1)
    month = yesterday.strftime('%m')
    year = yesterday.strftime('%Y')
    day1 = yesterday.strftime('%d')
    day2 = day.strftime('%d')
    print("date", year, month, day1, day2)
    return get_athena_data(year, month, day1, day2)


def lambda_handler(event, context):
    yesterday = date.today() - timedelta(days=1)
    month = yesterday.strftime('%m')
    year = yesterday.strftime('%Y')
    day1 = yesterday.strftime('%d')
    day2 = date.today().strftime('%d')
    dt = year + "-" + month + "-" + day1
    print("date", year, month, day1, day2)
    result = get_athen_data_by_date(date.today())
    yesterday_result = get_athen_data_by_date(date.today() - timedelta(days=1))

    if result:
        send_email(result, yesterday_result, dt)
    else:
        return None
