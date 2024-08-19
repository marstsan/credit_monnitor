from flask import Flask, redirect, url_for, render_template, request, Response, jsonify, session, g
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from lib.utils import *
from lib.DBActions import DBActions
from time import sleep
import yaml
import bcrypt
from datetime import datetime, timedelta


app = Flask(__name__)
app.secret_key = yaml.load(open('config.yaml'), Loader=yaml.FullLoader)['key']

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please login first.'


# default_data = {'create_service': '', 'service_ID_dict': {}, 'error': {}}
default_data = {'__error': {}}


class User(UserMixin):
    def __init__(self, username, password, role):
        self.id = username
        self.password = password
        self.role = role


@login_manager.user_loader
def load_user(username):
    return User(username, default_data['__users'][username]['password'], default_data['__users'][username]['role'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    default_data['__error'].clear()
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in default_data['__users'].keys() and check_password(password, default_data['__users'][username]['password']):
            user = User(username, password, default_data['__users'][username]['role'])
            login_user(user)
            default_data[current_user.id] = {'create_service': '', 'service_ID_dict': {}, 'error': {}, 'query_event': {}}
            return redirect(url_for('main'))
        else:
            default_data['__error']['login_error'] = 'Invalid username or password.'
    return render_template('login.html', error=default_data['__error'])


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/management')
@login_required
def management():
    try:
        default_data[current_user.id]['error'].clear()
    except:
        pass
    user_list = dba.get_user_list()

    return render_template('management.html', error=default_data[current_user.id]['error'], user_list=user_list)


@app.route('/create_user', methods=['POST'])
def create_user():
    username = request.form['create_user_email']
    displayname = request.form['create_user_displayname']
    password = request.form['create_user_pwd']
    role = request.form['create_user_role']
    user_list = dba.get_user_list()

    if displayname != '__users':
        if not dba.check_user_has_been_created(username):
            try:
                dba.create_user(username, password, displayname=displayname, role=role)
                default_data[current_user.id]['error']['create_user_error'] = f'Create user successfully.'
                user_list = dba.get_user_list()
                default_data['__users'] = dba.get_users()
            except Exception as e:
                default_data[current_user.id]['error']['create_user_error'] = f'Create user failed.\n{e}'
        else:
            default_data[current_user.id]['error']['create_user_error'] = f'The user [{username}] has been registered.'
    else:
        default_data[current_user.id]['error']['create_user_error'] = f'Displayname [{displayname}] is not allowed.'

    return render_template('management.html', error=default_data[current_user.id]['error'], user_list=user_list)


@app.route('/back')
@login_required
def back():
    if 'summary' in default_data[current_user.id].keys():
        service_ID = default_data[current_user.id]['selected_service_ID']
        summary = dba.get_summary(service_ID)
        events = dba.get_event(service_ID, skip=0, limit=20)
        for event in events:
            event['time'] = datetime_from_utc_to_local(event['time'])  # utc to local time

        return render_template('main.html', summary=summary, service_ID_list=default_data[current_user.id]['service_ID_list'],
                               events=events, error=default_data[current_user.id]['error'], current_user=current_user,
                               number_info_list=default_data[current_user.id]['number_info_list'])
    else:
        return redirect(url_for('main'))


@app.route('/', methods=['GET', 'POST'])
def index():
    return redirect('login')


@app.route('/main', methods=['GET', 'POST'])
@login_required
def main():
    # print(current_user.role)
    default_data['__error'].clear()
    try:
        default_data[current_user.id]['error'].clear()
    except:
        pass
    default_data[current_user.id]['service_ID_list'] = dba.get_service_id_list()

    if request.method == 'GET':
        return render_template('main.html', service_ID_list=default_data[current_user.id]['service_ID_list'], error=default_data[current_user.id]['error'],
                               current_user=current_user)

    elif request.method == 'POST':
        service_ID = request.form['query_service_ID']
        if service_ID == 'default':
            default_data[current_user.id]['error']['select_service_error'] = 'Please select a service ID'

            return render_template('main.html', error=default_data[current_user.id]['error'], current_user=current_user,
                                   service_ID_list=default_data[current_user.id]['service_ID_list'])

        else:
            summary = dba.get_summary(service_ID)
            number_info_list = dba.get_number_info_by_service(service_ID)

            # -- summary --
            summary['update_time'] = datetime_from_utc_to_local(summary['update_time'])     # utc to local time

            # -- number --
            for number in number_info_list:
                number['update_time'] = datetime_from_utc_to_local(number['update_time'])
                number['last_charge_time'] = datetime_from_utc_to_local(number['last_charge_time'])

            default_data[current_user.id]['summary'] = summary
            default_data[current_user.id]['selected_service_ID'] = service_ID
            default_data[current_user.id]['number_info_list'] = number_info_list

            events = dba.get_event(service_ID, skip=0, limit=20)
            for event in events:
                event['time'] = datetime_from_utc_to_local(event['time'])     # utc to local time

            return render_template('main.html', summary=default_data[current_user.id]['summary'], service_ID_list=default_data[current_user.id]['service_ID_list'],
                                   events=events, error=default_data[current_user.id]['error'], current_user=current_user,
                                   number_info_list=default_data[current_user.id]['number_info_list'])


@app.route('/create_tf', methods=['POST'])
def create_tf():
    # 取得 service ID, tf number, 並寫入 DB
    created = True
    try:
        default_data[current_user.id]['error'].clear()
    except:
        pass
    service_ID = request.form['create_service_ID']
    tf_number = request.form['create_tf_number']
    email = request.form['create_tf_email']

    try:
        if not dba.check_service_has_been_created(service_ID):
            dba.create_new_summary(service_ID, email)
        if not dba.check_number_has_been_created(service_ID, tf_number):
            dba.create_new_number(service_ID, tf_number)
        else:
            created = False
            default_data[current_user.id]['error']['create_error'] = f'Toll-free number [{tf_number}] on {service_ID} has been created in these system.'
    except Exception as e:
        created = False
        default_data[current_user.id]['error']['create_error'] = f'{e}'

    if created:
        dba.write_event(service_ID=service_ID, tf_number=tf_number, event_type='Create', username=current_user.id)

    sleep(1)
    events = dba.get_event(service_ID, skip=0, limit=20)
    for event in events:
        event['time'] = datetime_from_utc_to_local(event['time'])  # utc to local time

    # create number 後, summary 可以立即 rander, 需要回傳下列的值
    summary = dba.get_summary(service_ID)
    number_info_list = dba.get_number_info_by_service(service_ID)
    summary['update_time'] = datetime_from_utc_to_local(summary['update_time'])  # utc to local time

    for number in number_info_list:
        number['update_time'] = datetime_from_utc_to_local(number['update_time'])
        number['last_charge_time'] = datetime_from_utc_to_local(number['last_charge_time'])

    default_data[current_user.id]['summary'] = summary
    default_data[current_user.id]['number_info_list'] = number_info_list

    return render_template('main.html', events=events, service_ID=service_ID, service_ID_list=default_data[current_user.id]['service_ID_list'],
                           error=default_data[current_user.id]['error'], current_user=current_user, summary=default_data[current_user.id]['summary'],
                           number_info_list=default_data[current_user.id]['number_info_list'])


# @app.route('/get_tf_dropdown_options', methods=['POST'])
# def get_tf_dropdown_options():
#     selected_value = request.form.get('selectedValue')
#     # service ID 下拉選單沒選到就回 empty list; 選到回 service 內的所有 TF
#     if selected_value == 'default':
#         options = []
#     else:
#         if default_data[current_user.id]['service_ID_dict'] == {}:       # value disappear sometimes, reload the dict
#             default_data[current_user.id]['service_ID_dict'] = dba.get_service_id_dict()
#         options = default_data[current_user.id]['service_ID_dict'][selected_value]
#
#     return jsonify({'options': options})


@app.route('/update_tf', methods=['POST'])
def update_tf():
    try:
        default_data[current_user.id]['error'].clear()
    except:
        pass
    service_ID = default_data[current_user.id]['summary']['service_ID']
    number_info_list = default_data[current_user.id]['number_info_list']

    balance = dba.get_summary(service_ID)['balance']      # get the latest value
    topup = float(request.form['topup_edit'])
    topup_ticket = request.form['topup_ticket_edit']
    alert = float(request.form['alert_edit'])
    notification = request.form.get('notification_switch')
    notification = True if notification == 'on' else False  # 因為 switch 會回 on

    rate_in_list = request.form.getlist('rate_in_edit')
    float_rate_in_list = [float(x) for x in rate_in_list]
    rate_out_list = request.form.getlist('rate_out_edit')
    float_rate_out_list = [float(x) for x in rate_out_list]
    enable_list = []
    for i in range(len(number_info_list)):
        enable_list.append(request.form.get(f'enable_switch_{i+1}'))

    # print(float_rate_in_list, float_rate_out_list)

    if float(topup) != 0.0:
        # if balance + topup >= 0:
        #     dba.topup(service_ID, tf_number, balance=balance, topup=topup)
        #     dba.write_event('Top up', service_ID, tf_number, current_user.id, balance=balance, topup=topup, topup_ticket=topup_ticket)
        # else:
        #     default_data[current_user.id]['error']['topup_error'] = f'balance < 0 after topup, ignore this action.'

        dba.topup(service_ID, balance=balance, topup=topup)
        dba.write_event('Top up', service_ID, username=current_user.id, balance=balance, topup=topup, topup_ticket=topup_ticket)

    if default_data[current_user.id]['summary']['notification'] != notification or default_data[current_user.id]['summary']['alert'] != alert:
        default_data[current_user.id]['summary']['alert'] = alert
        default_data[current_user.id]['summary']['notification'] = notification
        dba.update_summary(service_ID, alert, notification)
        dba.write_event('Update', service_ID, username=current_user.id, alert=alert, notification=notification, sub_type='service')

    for i in range(len(number_info_list)):
        if number_info_list[i]['rate_in'] != float_rate_in_list[i] or number_info_list[i]['rate_out'] != float_rate_out_list[i] or number_info_list[i]['enabled'] != (True if enable_list[i] == 'on' else False):
            default_data[current_user.id]['number_info_list'][i]['rate_in'] = float_rate_in_list[i]
            default_data[current_user.id]['number_info_list'][i]['rate_out'] = float_rate_out_list[i]
            default_data[current_user.id]['number_info_list'][i]['enabled'] = enable_list[i]
            dba.update_number(service_ID, number_info_list[i]['number'], float_rate_in_list[i], float_rate_out_list[i], True if enable_list[i] == 'on' else False)
            number_enable = 'enabled' if enable_list[i] == 'on' else 'disabled'
            dba.write_event('Update', service_ID, username=current_user.id, tf_number=number_info_list[i]['number'], rate_in=float_rate_in_list[i], rate_out=float_rate_out_list[i],
                            number_enable=number_enable, sub_type='number')

    sleep(1)
    events = dba.get_event(service_ID, 0, 20)
    for event in events:
        event['time'] = datetime_from_utc_to_local(event['time'])  # utc to local time

    summary = dba.get_summary(service_ID)
    number_info_list = dba.get_number_info_by_service(service_ID)
    summary['update_time'] = datetime_from_utc_to_local(summary['update_time'])  # utc to local time

    for number in number_info_list:
        number['update_time'] = datetime_from_utc_to_local(number['update_time'])
        number['last_charge_time'] = datetime_from_utc_to_local(number['last_charge_time'])

    default_data[current_user.id]['summary'] = summary
    default_data[current_user.id]['number_info_list'] = number_info_list

    return render_template('main.html', summary=default_data[current_user.id]['summary'], service_ID_list=default_data[current_user.id]['service_ID_list'],
                           service_ID=service_ID, events=events, error=default_data[current_user.id]['error'], current_user=current_user,
                           number_info_list=number_info_list)


@app.route('/more_events', methods=['POST'])
def more_events():
    service_ID = default_data[current_user.id]['selected_service_ID']
    # tf_number = default_data[current_user.id]['selected_tf_number']
    number_info_list = default_data[current_user.id]['number_info_list']
    alert = default_data[current_user.id]['summary']['alert']
    default_start_date = (datetime.today() - timedelta(days=6)).strftime('%Y-%m-%d')
    default_end_date = datetime.today().strftime('%Y-%m-%d')
    default_data[current_user.id]['query_event']['start_date'], default_data[current_user.id]['query_event']['end_date'] = default_start_date, default_end_date
    selected_date_range = None
    default_event_types_checked_status = {'Create': True, 'Topup': True, 'Update': True, 'Charge': False, 'Notify': False}

    local_start_time = datetime.strptime(default_start_date + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
    local_end_time = datetime.strptime(default_end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
    utc_start_time = datetime_from_local_to_utc(local_start_time)
    utc_end_time = datetime_from_local_to_utc(local_end_time)

    # get chart data
    x, y, notify = dba.get_balance_chart_coordinator(service_ID, alert, start_time=utc_start_time, end_time=utc_end_time)
    x_local_time = []
    for _x in x:
        x_local_time.append(datetime_from_utc_to_local(_x))

    # get event data
    events = dba.get_event(service_ID, start_time=utc_start_time, end_time=utc_end_time, event_types=['Create', 'Top up', 'Update'])
    for event in events:
        event['time'] = datetime_from_utc_to_local(event['time'])  # utc to local time

    return render_template('more_events.html', service_ID=service_ID, start_date=default_start_date, end_date=default_end_date,
                           error=default_data[current_user.id]['error'], events=events, event_types_checked_status=default_event_types_checked_status,
                           selected_date_range=selected_date_range, x=x_local_time, y=y, notify=notify, summary=default_data[current_user.id]['summary'])


@app.route('/more_events_query', methods=['POST'])
def more_events_query():
    try:
        default_data[current_user.id]['error'].clear()
    except:
        pass
    service_ID = default_data[current_user.id]['selected_service_ID']
    # tf_number = default_data[current_user.id]['selected_tf_number']
    number_info_list = default_data[current_user.id]['number_info_list']
    alert = default_data[current_user.id]['summary']['alert']
    selected_start_date = default_data[current_user.id]['query_event']['start_date']
    selected_end_date = default_data[current_user.id]['query_event']['end_date']
    utc_start_time = None
    utc_end_time = None

    selected_date_range = request.form.get('date_checkbox')

    if selected_date_range is None:
        selected_start_date = request.form['start_date']
        selected_end_date = request.form['end_date']
        default_data[current_user.id]['query_event']['start_date'], default_data[current_user.id]['query_event']['end_date'] = selected_start_date, selected_end_date

        local_start_time = datetime.strptime(selected_start_date + ' 00:00:00', '%Y-%m-%d %H:%M:%S')
        local_end_time = datetime.strptime(selected_end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
        utc_start_time = datetime_from_local_to_utc(local_start_time)
        utc_end_time = datetime_from_local_to_utc(local_end_time)

    events = []
    event_types = []
    event_types_checked_status = {}
    for event_type in all_event_types:
        if request.form.get(event_type) is not None:
            event_types_checked_status['Topup' if event_type == 'Top up' else event_type] = True
            event_types.append(event_type)
        else:
            event_types_checked_status[event_type] = False

    # get chart data
    x, y, notify = dba.get_balance_chart_coordinator(service_ID, alert, start_time=utc_start_time, end_time=utc_end_time)
    x_local_time = []
    for _x in x:
        x_local_time.append(datetime_from_utc_to_local(_x))

    # get event data
    if len(event_types) > 0:
        events = dba.get_event(service_ID, start_time=utc_start_time, end_time=utc_end_time, event_types=event_types)
        for event in events:
            event['time'] = datetime_from_utc_to_local(event['time'])  # utc to local time

    # default_data[current_user.id]['error']['query_event_error'] = 'Please select at least one type.'

    return render_template('more_events.html', service_ID=service_ID, start_date=selected_start_date, end_date=selected_end_date,
                           error=default_data[current_user.id]['error'], events=events, event_types_checked_status=event_types_checked_status,
                           selected_date_range=selected_date_range, x=x_local_time, y=y, notify=notify, summary=default_data[current_user.id]['summary'])


def check_password(plain_password, hashed_password):

    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)


@app.route('/change_pwd', methods=['POST'])
def change_pwd():
    try:
        default_data[current_user.id]['error'].clear()
    except:
        pass
    pwd1 = request.form['pwd1']
    pwd2 = request.form['pwd2']
    if pwd1 == pwd2:
        try:
            dba.update_password(current_user.id, pwd1)
            default_data[current_user.id]['error']['change_pwd_error'] = 'Change password successfully.'
            default_data['__users'] = dba.get_users()
        except Exception as e:
            default_data[current_user.id]['error']['change_pwd_error'] = f'Change password failed.\n{e}'
    else:
        default_data[current_user.id]['error']['change_pwd_error'] = 'Password not match, password is not changed.'

    return render_template('main.html', service_ID_list=default_data[current_user.id]['service_ID_list'], error=default_data[current_user.id]['error'], current_user=current_user)


if __name__ == '__main__':
    dba = DBActions()

    # service_ID_dict = dba.get_service_id_dict()
    default_data['__users'] = dba.get_users()
    all_event_types = ['Create', 'Top up', 'Update', 'Charge', 'Notify']

    app.run(host='0.0.0.0', port=8080, debug=True)


# loclx account login
# wZStmPhmHp2SbPxgMTQE1WWqhC7CTnLmobTF1kcN              token copied from website: https://localxpose.io/dashboard/access
# marstsan@gmail.com / Kuma1208+
# loclx tunnel http --reserved-domain callmonitor.ap.loclx.io http --to localhost:80