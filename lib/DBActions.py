import asyncio

import pymongo
import yaml
from datetime import datetime
import bcrypt
from .utils import *


class DBActions:
    def __init__(self):
        config = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)['DBActions']
        uri = config['uri']
        self.dbclient = pymongo.MongoClient(uri)
        self.db = self.dbclient['credit_monitor_v2']
        self.collection_event = self.db['event']
        self.collection_summary = self.db['summary']
        self.collection_number = self.db['number']
        self.collection_user = self.db['user']

        self.alert_threshold = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)['alert threshold']

    def create_new_summary(self, service_ID, email):
        time = datetime.utcnow()
        data = {
            'service_ID': service_ID,
            'email': email,
            'balance': 0.0,
            'notification': True,
            'rate_in': 0.0,
            'rate_out': 0.0,
            'alert': 30.0,
            'create_time': time,
            'update_time': time,
            # 'last_charge_time': time,
            'last_topup_balance': 0.0
        }
        self.collection_summary.insert_one(data)

    def create_new_number(self, service_ID, number):
        time = datetime.utcnow()
        data = {
            'service_ID': service_ID,
            'number': number,
            'rate_in': 0.0,
            'rate_out': 0.0,
            'enabled': True,
            'create_time': time,
            'update_time': time,
            'last_charge_time': time,
        }
        self.collection_number.insert_one(data)

    def get_service_id_dict(self):
        service_ID_dict = {}
        for summary in self.collection_summary.find():
            if summary['service_ID'] not in service_ID_dict.keys():
                service_ID_dict[summary['service_ID']] = [summary['tf_number']]
            else:
                service_ID_dict[summary['service_ID']].append(summary['tf_number'])

        return service_ID_dict

    def get_service_id_list(self):
        service_id_list = []
        for summary in self.collection_summary.find():
            service_id_list.append(summary['service_ID'])
        return service_id_list

    def get_summary(self, service_ID):
        query = {'service_ID': service_ID}
        summary = self.collection_summary.find_one(query)

        return summary

    def get_number_info_by_service(self, service_ID):
        query = {'service_ID': service_ID}
        # cursor = self.collection_number(query)
        number_info_list = list(self.collection_number.find(query))
        return number_info_list

    def update_summary(self, service_ID, alert, notification):
        time = datetime.utcnow()
        query = {'service_ID': service_ID}
        self.collection_summary.update_one(query, {'$set': {'alert': alert, 'notification': notification, 'update_time': time}})

    def update_number(self, service_ID, number, rate_in, rate_out, enabled):
        time = datetime.utcnow()
        query = {'service_ID': service_ID, 'number': number}
        self.collection_number.update_one(query, {'$set': {'rate_in': rate_in, 'rate_out': rate_out, 'enabled': enabled, 'update_time': time}})

    def topup(self, service_ID, balance, topup):
        time = datetime.utcnow()
        balance_new = round(balance + topup, 3)
        query = {'service_ID': service_ID}
        self.collection_summary.update_one(query, {'$set': {'balance': balance_new, 'update_time': time, 'last_topup_balance': balance_new}})

    def write_event(self, event_type, service_ID, tf_number=None, username=None, balance=None, topup=None, topup_ticket=None,
                    rate_in=None, rate_out=None, alert=None, notification=True, charge_start_time=None, charge_end_time=None,
                    total_charge=None, last_topup_balance=None, number_enable=None, description=None, sub_type=None):
        time = datetime.utcnow()
        displayname = self.collection_user.find_one({'username': username})['displayname'] if username is not None else None
        data = {
            'service_ID': service_ID,
            'tf_number': tf_number,
            'type': event_type,
            'sub_type': sub_type,
            'time': time,
            'balance': balance,
            'topup': topup,
            'topup_ticket': topup_ticket,
            'rate_in': rate_in,
            'rate_out': rate_out,
            'alert': alert,
            'notification': notification,
            'number_enable' : number_enable,
            'charge_start_time': charge_start_time,
            'charge_end_time': charge_end_time,
            'total_charge': total_charge,
            'last_topup_balance': last_topup_balance,
            'displayname': displayname
        }
        if event_type == 'Create':
            data['description'] = f'{displayname} - Create new toll-free number [{tf_number}] on {service_ID}.'

        elif event_type == 'Update':
            if sub_type == 'service':
                data['sub_type'] = sub_type
                data['alert'] = alert
                data['notification'] = notification
                data['description'] = f'{displayname} - update alert to [{alert}] and turn [{"on" if notification == True else "off"}] the notification.'
            elif sub_type == 'number':
                data['sub_type'] = sub_type
                data['rate_in'] = rate_in
                data['rate_out'] = rate_out
                data['number_enable'] = number_enable
                data['description'] = f'{displayname} - update inbound rate to [{rate_in}], outbound rate to [{rate_out}] for number [{tf_number}] ' \
                                      f'and the number is {number_enable}.'

        elif event_type == 'Top up':
            data['topup'] = topup
            data['balance'] = balance
            data['description'] = f'{displayname} - Top up ${topup}, balance from ${balance} to ${round(topup+balance, 3)}'
            if len(topup_ticket) > 0:
                data['description'] += f' (Ticket: {topup_ticket})'

        elif event_type == 'Charge':
            data['charge_start_time'] = charge_start_time
            data['charge_end_time'] = charge_end_time
            data['total_charge'] = total_charge
            data['description'] = f'[{datetime_from_utc_to_local(charge_start_time)} ~ {datetime_from_utc_to_local(charge_end_time)}] ' \
                                  f'The balance is from ${balance} to ${round(balance - total_charge, 3)}'
            data['description'] += description

        elif event_type == 'Notify':
            data['balance'] = balance
            data['alert'] = alert
            data['total_charge'] = total_charge
            data['last_topup_balance'] = last_topup_balance
            check_balance = (balance - total_charge) / last_topup_balance
            if balance - total_charge < 0:
                data['description'] = f'Notification sent because balance is ${round(balance - total_charge, 3)}'
            else:
                data['description'] = f'Notification sent because {round(balance - total_charge, 3)}/{last_topup_balance}' \
                                      f' = {round(check_balance * 100, 3)}% (current balance/last topup balance) is lower than {round(alert, 3)}%'

        self.collection_event.insert_one(data)

    def get_event(self, service_ID, skip=0, limit=None, start_time=None, end_time=None, event_types=None, sort=pymongo.DESCENDING):
        query = {'service_ID': service_ID}
        if start_time is not None:
            if 'time' not in query.keys():
                query['time'] = {}
            query['time']['$gte'] = start_time
        if end_time is not None:
            if 'time' not in query.keys():
                query['time'] = {}
            query['time']['$lte'] = end_time
        if event_types is not None and len(event_types) > 0:
            type_list = []
            for event_type in event_types:
                type_list.append({'type': event_type})
            query['$or'] = type_list

        if limit is None:
            cursor = self.collection_event.find(query).sort('time', sort).skip(skip)      # pymongo.ASCENDING, pymongo.DESCENDING 為降冪
        else:
            cursor = self.collection_event.find(query).sort('time', sort).skip(skip).limit(limit)

        events = list(cursor)

        return events

    def get_all_notify_values(self, service_ID, alert):
        events = self.get_event(service_ID, event_types=['Create', 'Update', 'Top up', 'Charge'], sort=pymongo.ASCENDING)
        notify_value = float(0)
        alert = 30.0
        all_notify = []
        balance = 0
        for event in events:
            if event['type'] == 'Create':
                all_notify.append({event['time']: notify_value})
            elif event['type'] == 'Update':
                if event['sub_type'] == 'service':
                    alert = float(event['description'].split('[')[1].split(']')[0])
            elif event['type'] == 'Top up':
                if ' (' in event['description']:
                    balance = float(event['description'].split(' (')[0].split('$')[-1])
                else:
                    balance = float(event['description'].split('$')[-1])
                notify_value = round(balance * alert / 100, 3)
                if notify_value < 0:
                    notify_value = 0
                all_notify.append({event['time']: notify_value})
            elif event['type'] == 'Charge':
                notify_value = round(balance * alert / 100, 3)
                if notify_value < 0:
                    notify_value = 0
                all_notify.append({event['time']: notify_value})

        return all_notify

    def get_balance_chart_coordinator(self, service_ID, alert, start_time=None, end_time=None):
        query = {'service_ID': service_ID}
        if start_time is not None:
            if 'time' not in query.keys():
                query['time'] = {}
            query['time']['$gte'] = start_time
        if end_time is not None:
            if 'time' not in query.keys():
                query['time'] = {}
            query['time']['$lte'] = end_time

        cursor = self.collection_event.find(query).sort('time', pymongo.ASCENDING)
        events = list(cursor)

        self.collection_summary.find_one(query)

        x, y = [], []
        for event in events:
            if event['type'] == 'Create':
                balance = float(0)
                x.append(event['time'])
                y.append(balance)
            elif event['type'] == 'Top up':
                if ' (' in event['description']:
                    balance = float(event['description'].split(' (')[0].split('$')[-1])
                else:
                    balance = float(event['description'].split('$')[-1])
                x.append(event['time'])
                y.append(balance)
            elif event['type'] == 'Charge':
                balance = event['balance'] - event['total_charge']
                x.append(event['time'])
                y.append(balance)

        all_notify = self.get_all_notify_values(service_ID, alert)
        notify = []
        for n in all_notify:
            if list(n.keys())[0] in x:
                notify.append(list(n.values())[0])

        return x, y, notify

    def get_all_summary(self):
        all_summary = list(self.collection_summary.find())

        return all_summary

    def charge(self, service_ID, balance, total_charge):
        time = datetime.utcnow()
        # update summary
        query = {'service_ID': service_ID}
        self.collection_summary.update_one(query, {'$set': {'balance': round(balance - total_charge, 3), 'update_time': time}})

    def number_update_last_charge_time(self, service_ID, number, end_time):
        query = {'service_ID': service_ID, 'number': number}
        self.collection_number.update_one(query, {'$set': {'last_charge_time': end_time}})

    def check_service_has_been_created(self, service_ID):
        summary = self.get_summary(service_ID)
        if summary is None:
            return False
        else:
            return True

    def check_number_has_been_created(self, service_ID, number):
        query = {'service_ID': service_ID, 'number': number}
        query_result = self.collection_number.find_one(query)
        if query_result is None:
            return False
        else:
            return True

    def create_user(self, email, password, role='user', displayname=''):
        data = {'username': email,
                'password': self.hash_password(password),
                'role': role,
                'displayname': displayname}
        self.collection_user.insert_one(data)

    def check_user_has_been_created(self, username):
        query = {'username': username}
        user = self.collection_user.find_one(query)
        if user is None:
            return False
        else:
            return True

    def get_user_list(self):
        user_list = list(self.collection_user.find())

        return user_list

    def get_users(self):
        users = {}
        users_data = list(self.collection_user.find())
        for user_data in users_data:
            users[user_data['username']] = {'password': user_data['password'], 'role': user_data['role'], 'displayname': user_data['displayname']}

        return users

    def update_password(self, username, password):
        hashed_password = self.hash_password(password)
        query = {'username': username}
        self.collection_user.update_one(query, {'$set': {'password': hashed_password}})

    @staticmethod
    def hash_password(plain_password):
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(plain_password.encode('utf-8'), salt)
        return hashed_password

    def delete_event_by_TF(self, tf_number):
        query = {'tf_number': tf_number}
        self.collection_event.delete_many(query)

    def get_usage_by_TF(self, service_ID, tf_number, start_time=None, end_time=None):
        events = self.get_event(service_ID, tf_number, event_types=['Charge'], start_time=start_time, end_time=end_time)
        usage_list = []
        total_usage = 0
        for event in events:
            minute = int(event['description'].split('[')[1].split(']')[0])
            if minute != 0:
                usage_list.append(minute)
            total_usage += minute
        print(usage_list)
        print(total_usage)

    # def edit_charge_description(self, service_ID, tf_number):
    #     events = self.get_event(service_ID, tf_number, event_types=['Charge'], sort=pymongo.ASCENDING)
    #     for event in events:
    #         service_ID = event['service_ID']
    #         tf_number = event['tf_number']
    #         time = event['time']
    #         minute = int(int(event['description'].split('[')[1].split(']')[0])/2)
    #         charge_start_time = event['description'].split('[')[2][:19]
    #         charge_end_time = event['description'].split('[')[2][22:41]
    #         summary = self.get_summary(service_ID, tf_number)
    #         balance = summary['balance']
    #         rate = summary['rate']
    #
    #
    #         description = f'Total usage [{minute}] minutes [{charge_start_time} ~ {charge_end_time} UTC time]' \
    #                               f'\nCharge {rate} (rate) x {minute} (usage minutes) = ${round(rate * minute, 3)}' \
    #                               f'\nThe balance is from ${balance} to ${round(balance - rate * minute, 3)}'
    #
    #         # print(charge_start_time, charge_end_time)
    #         # if minute != 0:
    #         #     print('before', event['description'])
    #         #     print('after', description)
    #
    #         event_query = {'service_ID': service_ID, 'tf_number': tf_number, 'time': time}
    #         self.collection_event.update_one(event_query, {'$set': {'description': description}})
    #
    #         if minute != 0:
    #             summary_query = {'service_ID': service_ID, 'tf_number': tf_number}
    #             self.collection_summary.update_one(summary_query, {'$set': {'balance': round(balance - rate * minute, 3)}})

