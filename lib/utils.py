from datetime import datetime
import time
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import pathlib


def datetime_from_utc_to_local(utc_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    local_datetime = utc_datetime + offset

    # return local_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]       # return to digit 3
    return local_datetime.strftime('%Y-%m-%d %H:%M:%S')     # return to second


def datetime_from_local_to_utc(local_datetime):
    now_timestamp = time.time()
    offset = datetime.fromtimestamp(now_timestamp) - datetime.utcfromtimestamp(now_timestamp)
    utc_datetime = local_datetime - offset

    # return local_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]       # return to digit 3
    return utc_datetime    # return utc in datetime format


def send_email(email_to_list, mail_title, text):
    # me == my email address
    # you == recipient's email address
    me = "rickchentest@gmail.com"
    you = ', '.join(email_to_list)

    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart('alternative')
    msg['Subject'] = mail_title
    msg['From'] = me
    msg['To'] = you

    # Record the MIME types of both parts - text/plain and text/html.
    part1 = MIMEText(text, 'plain')

    # Attach parts into message container.
    # According to RFC 2046, the last part of a multipart message, in this case
    # the HTML message, is best and preferred.
    msg.attach(part1)

    with smtplib.SMTP(host="smtp.gmail.com", port=587) as smtp:  # 設定SMTP伺服器
        try:
            smtp.ehlo()  # 驗證SMTP伺服器
            smtp.starttls()  # 建立加密傳輸
            # app password for gmail please reference https://www.learncodewithmike.com/2020/02/python-email.html
            smtp.login("rickchentest@gmail.com", "pjfmuduvtesdtraj")  # 登入寄件者gmail
            smtp.sendmail(me, you, msg.as_string())
        except Exception as e:
            print("Error message: ", e)


def create_folder(folder_name):
    pathlib.Path(folder_name).mkdir(parents=True, exist_ok=True)
