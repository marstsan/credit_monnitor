from lib.DBActions import DBActions
from lib.CinnoxTool import CinnoxTool
from lib.ElasticSearch import ElasticSearch
from lib.utils import *
from datetime import datetime
import yaml
from time import sleep
import logging


# log
create_folder('log')
level = logging.INFO
file_path = f'log/charge_{datetime.today().strftime("%Y-%m-%d")}.txt'
logging.basicConfig(filename=file_path, encoding='utf-8', format='[%(asctime)s] [%(levelname)5s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

logger = logging.getLogger()
logger.setLevel(level)

logger.info('start charging')
alert_threshold = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)['alert threshold']
default_email_to_list = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)['SendEmail']['default_to']

dba = DBActions()
ct = CinnoxTool()
es = ElasticSearch()

all_summary = dba.get_all_summary()

for summary in all_summary:
    # charge
    end_time = datetime.utcnow().replace(minute=0, second=0, microsecond=0)

    service_ID = summary['service_ID']
    number_info_list = dba.get_number_info_by_service(service_ID)
    enabled_number_info_list = []
    for number_info in number_info_list:
        if number_info['enabled']:
            enabled_number_info_list.append(number_info)

    email = summary['email']
    balance = summary['balance']
    alert = summary['alert']
    last_topup_balance = summary['last_topup_balance']

    email_to_list = default_email_to_list[:]        # copy list to prevent duplicate items
    email_to_list.append(email)
    _start_time = None

    total_charge = 0
    description = ''
    if enabled_number_info_list:
        for number_info in enabled_number_info_list:
            number, rate_in, rate_out = number_info['number'], number_info['rate_in'], number_info['rate_out']
            start_time = number_info['last_charge_time']
            if _start_time is None:
                _start_time = start_time
            elif _start_time > start_time:
                _start_time = start_time
            usage_in = es.get_tf_usage(service_ID, number, start_time, end_time, 'inbound')
            usage_out = es.get_tf_usage(service_ID, number, start_time, end_time, 'outbound')
            total_charge += round(usage_in * rate_in + usage_out * rate_out, 3)
            description += f"\n- Number [{number}]\n\tinbound usage [{usage_in}] minutes, charge {rate_in} (rate) x {usage_in} (minutes) = ${round(rate_in * usage_in, 3)}"
            description += f"\n\toutbound usage [{usage_out}] minutes, charge {rate_out} (rate) x {usage_out} (minutes) = ${round(rate_out * usage_out, 3)}"
            dba.number_update_last_charge_time(service_ID, number, end_time)

        dba.charge(service_ID, balance, total_charge)
        dba.write_event('Charge', service_ID, balance=balance, total_charge=total_charge,
                        charge_start_time=_start_time, charge_end_time=end_time, description=description)

    sleep(0.05)

    # notify
    if summary['notification']:         # if notification is turn on (by TF)
        if last_topup_balance != 0:
            check_balance = (balance - total_charge) / last_topup_balance
            text = ''
            notify = True

            # 餘額為負數
            if balance - total_charge < 0:
                text = f'[{service_ID}] - {email}\n'
                text += f'Balance [{round(balance - total_charge, 3)}] is lower than 0, ' \
                        f'PLEASE CONTACT THE CUSTOMER IMMEDIATELY.'
            # 餘額低於 最低% (yaml)
            elif check_balance <= alert_threshold['level 2']:
                text = f'[{service_ID}] - {email}\n'
                text += f'{round(balance - total_charge, 3)}/{last_topup_balance} = {round(check_balance * 100, 3)}% ' \
                        f'(current balance/last topup balance) is lower than {alert_threshold["level 2"] * 100}%, ' \
                        f'PLEASE CONTACT THE CUSTOMER IMMEDIATELY.'

            # 餘額低於 自訂 % (mongoDB)
            elif check_balance <= alert / 100:
                text = f'[{service_ID}] - {email}\n'
                text += f'{round(balance - total_charge, 3)}/{last_topup_balance} = {round(check_balance * 100, 3)}% ' \
                        f'(current balance/last topup balance) is lower than {round(alert, 3)}%.' \

            # 餘額足夠無需通知
            else:
                notify = False

            # 送出通知如果需要通知
            if notify:
                # send notification to space
                ct.send_message_to_room(text)

                # email to someone
                title = f'[{service_ID}] : balance alert'
                send_email(email_to_list, title, text)
                dba.write_event('Notify', service_ID, balance=balance, alert=alert, total_charge=total_charge, last_topup_balance=last_topup_balance)
