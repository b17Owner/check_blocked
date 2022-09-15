#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
Created on Aug 22, 2022

@author: b17Own


ToDo:
+ добавить номера строк
+ функция check_endpoint должна записать результат проверки в файл
+ добавить многопоточность
+ Разделить СТАТУС и ОТВЕТ ОШИБКИ
+ Добавить получение нового списка url с ftp
+ Исправить ; в url, для файла отчета (разделитель |)
+ Добавить args и .env для конфигурации параметров
+ Завернуть в докер для разделения на разные списки url, domain, ip
+ Добавить response.url в коммент, если доступ не блокируется
+ Добавить в название репорта дату проверки
+ Функцию для логгирования в stdout
+ Добавить время в app лог
+ Добавить исключения в smtp
+ Добавить default, если в конфиге не указано значение
+ Добавить argparse и для опредение FILENAME через аргументы
+ Залить на гит
+ Сделать логгирование приложения и детальный отчёт в разные файлы (решается перенаправлением stdout в файл)
'''

import requests
import os
import sys
import threading
import time
import argparse
from datetime import datetime
from dotenv import dotenv_values
import logging

# # Модуль для ограничения использования CPU
# import resource

# модули отправки email
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders

# модули для FTP
import ftplib


#
#   Вспомогательная функция для округления значений float
#
def to_fixed(number, decimal=2):
    return f'{number:.{decimal}f}'


#
#   Функция проверки конфига
#   обязательные параметры и default значения
#
def check_config(config, args):
    # Список всех ключей .env
    all_values = {
        'DEBUG': '0',
        'DEBUG_LIMIT': '100',
        'FILENAME': 'url.list',
        'REPORT_FILE': '',
        'BLOCK_DOMAIN': 'zapret.local',
        'WORKERS': '20',
        'FTP_ENABLE': '0',
        'FTP_SERVER': '127.0.0.1',
        'FTP_PORT': '21',
        'FTP_LOGIN': 'anonymous',
        'FTP_PASSWORD': '',
        'FTP_UPLOAD': '0',
        'SMTP_ENABLE': '0',
        'SMTP_SERVER': '127.0.0.1',
        'SMTP_PORT': '25',
        'SMTP_LOGIN': '',
        'SMTP_PASSWORD': '',
        'SMTP_ATTACH_REPORT': '0',
        'SMTP_RECIPIENTS': '',
    }

    # Список обязательных ключей .env
    required_values = []

    # Проверяем все ли обязательные ключи и значения указаны
    for key in required_values:
        if key not in config.keys():
            print(f'В файле .env отсутствует ключ: {key}')
            sys.exit(0)
        if config[key] == '':
            print(f'Не указано значение обязательного ключа {key}')
            sys.exit(0)

    # Заполняем значениями по умолчанию, не указанные в конфиге
    for key in all_values.keys():
        if key not in config.keys():
            config[key] = all_values[key]
        if config[key] == '':
            config[key] = all_values[key]

    if args.debug is True:
        config['DEBUG'] = '1'

    if args.file:
        config['FILENAME'] = args.file

    if args.response:
        config['BLOCK_DOMAIN'] = args.response

    # Форматируем значения чисел из str в int
    config['DEBUG_LIMIT'] = int(config['DEBUG_LIMIT'])
    config['WORKERS'] = int(config['WORKERS'])

    # Форматируем название файла с отчетом
    if config['REPORT_FILE'] == '':
        config['REPORT_FILE'] = ('reports/'
                                 + config['FILENAME']
                                 + '_report_'
                                 + time.strftime('%d%m%Y%H%M')
                                 + '.log'
                                 )
    else:
        config['REPORT_FILE'] = time.strftime(config['REPORT_FILE'])


#
# Функция для логгирования с меткой времени в stdout
#
def log_stdout(message):
    print(f"{time.strftime('%d-%m-%Y %H:%M')} LOG: {message}")


#
#   Функция для загрузки списка url с ftp
#
def ftp_download():
    log_stdout(f'Загрузка файла со списком url c FTP {config["FTP_SERVER"]}')
    filename = config['FILENAME']
    ftp = ftplib.FTP(config['FTP_SERVER'])
    try:
        ftp.login(config['FTP_LOGIN'], config['FTP_PASSWORD'])
    except ftplib.all_errors as err:
        log_stdout(f'Ошибка подключения к FTP: {err}')
        sys.exit(0)

    try:
        ftp.retrbinary('RETR ' + filename, open(filename, 'wb').write)
    except IOError:
        log_stdout('Ошибка получения файла по ftp')


#
#   Функция для загрузки файла с отчетом на ftp
#
def ftp_upload():
    log_stdout(f'Загрузка файла отчёта на FTP {config["FTP_SERVER"]}')
    filename = config['REPORT_FILE']
    ftp = ftplib.FTP(config['FTP_SERVER'])
    try:
        ftp.login(config['FTP_LOGIN'], config['FTP_PASSWORD'])
    except ftplib.all_errors as err:
        log_stdout(f'Ошибка подключения к FTP: {err}')
        sys.exit(0)

    try:
        ftp.storbinary('STOR ' + filename, open(filename, 'rb'))
    except IOError:
        log_stdout('Ошибка загрузки фала на ftp')


#
#   Функция отправки отчета на почту
#
def send_report(msg_text, attachment):
    log_stdout(f'Отправка отчета на {config["SMTP_RECIPIENTS"]}')
    # Собираем письмо из частей
    msg = MIMEMultipart()
    msg.attach(MIMEText(msg_text, 'plain'))
    msg['From'] = config['SMTP_LOGIN']
    msg['To'] = config['SMTP_RECIPIENTS']

    subject = u'Отчёт по блокировке РКН: ' + config['FILENAME']

    # Если кол-во незаблокированных больше порога, тогда добавить ALARM
    percent_unblocked = statistics['not_blocked'] * 100 / statistics['all']
    if percent_unblocked >= 1:
        subject += ' ALARM!!! ' + str(to_fixed(percent_unblocked)) + '%'

    msg['Subject'] = subject

    # Если включена отправка файла с отчетом
    if config['SMTP_ATTACH_REPORT'] == '1':
        # Формируем часть письма с файлом отчета
        basename = os.path.basename(attachment)
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(attachment, "rb").read())
        encoders.encode_base64(part)
        part.add_header(
            'Content-Disposition',
            'attachment; filename="%s"' % basename
        )
        msg.attach(part)

    # Авторизуемся на SMTP
    s = smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT'])
    s.esmtp_features['auth'] = 'LOGIN DIGEST-MD5 PLAIN'
    try:
        s.login(config['SMTP_LOGIN'], config['SMTP_PASSWORD'])
    except smtplib.SMTPException as err:
        log_stdout(f'Ошибка подключения к SMTP {err}')
        sys.exit()

    # Отправляем письмо
    s.sendmail(
        config['SMTP_LOGIN'],
        config['SMTP_RECIPIENTS'].split(','),
        msg.as_string()
    )
    s.quit()


#
#   Функция для записи в файл результатов проверки
#
#   result = {
#       'id': int,
#       'url': str,
#       'status': str,
#       'comment': str,
#       'check_count': int
#   }
def report_item(result):
    logger.info(f'\
{result["id"]}|\
{result["url"]}|\
{result["status"]}|\
{result["comment"]}|\
{result["check_count"]}|\
{result["datetime_check"]}')


#
#   Функция проверки эндпоинта, со счетчиком проверок
#
def check_endpoint(id, url, check_count=1):
    # Подключаем глобальную переменную для подсчета статистики
    global statistics

    # Очищаем url от переносов строки
    url = url.replace('\r', '')
    url = url.replace('\n', '')

    # Если в начале url *. то убрать эту часть для проверки корневого домена
    if url[0:2].lower() == '*.':
        url = url[2:]

    # Если в url отсутствует часть http
    if url[0:5].lower() != 'http:':
        url = 'http://' + url

    # Инкрементируем счетчик всех записей, если первая проверка
    if check_count == 1:
        statistics['all'] += 1
    try:
        response = requests.head(url, timeout=20)

        if response.status_code == 302:
            response.url = response.next.url

        # Если url в ответе содержит blocked.mts.ru, значит сработала
        # блокировка MTS
        if response.url.split("/")[2] == config['BLOCK_DOMAIN']:
            statistics['blocked'] += 1
            result = {
                'id': id,
                'url': url,
                'status': 'ЗАБЛОКИРОВАНО',
                'comment': '',
                'check_count': check_count,
                'datetime_check': datetime.now()
            }
            report_item(result)
        else:
            statistics['not_blocked'] += 1
            result = {
                'id': id,
                'url': url,
                'status': 'НЕ ЗАБЛОКИРОВАНО',
                'comment': response.url,
                'check_count': check_count,
                'datetime_check': datetime.now()
            }
            report_item(result)
    except requests.exceptions.ConnectionError as err:
        # Если кол-во проверок меньше 3, то провести повторную
        # проверку
        if check_count < 3:
            time.sleep(1)
            check_endpoint(id, url, check_count + 1)

        # Если кол-во проверок >3, записать результат
        if check_count == 3:
            statistics['error_connection'] += 1
            result = {
                'id': id,
                'url': url,
                'status': 'ОШИБКА СОЕДИНЕНИЯ',
                'comment': str(err.args[0]),
                'check_count': check_count,
                'datetime_check': datetime.now()
            }
            report_item(result)

    except requests.exceptions.ReadTimeout as err:
        statistics['error_read'] += 1
        result = {
            'id': id,
            'url': url,
            'status': 'ОШИБКА ЧТЕНИЯ ПОТОКА',
            'comment': str(err.args[0]),
            'check_count': check_count,
            'datetime_check': datetime.now()
        }
        report_item(result)
    except requests.exceptions.ChunkedEncodingError as err:
        statistics['error_peer'] += 1
        result = {
            'id': id,
            'url': url,
            'status': 'ОШИБКА ПИРА',
            'comment': str(err.args[0]),
            'check_count': check_count,
            'datetime_check': datetime.now()
        }
        report_item(result)
    except requests.exceptions.InvalidURL as err:
        statistics['error_url'] += 1
        result = {
            'id': id,
            'url': url,
            'status': 'ОШИБКА URL',
            'comment': str(err.args[0]),
            'check_count': check_count,
            'datetime_check': datetime.now()
        }
        report_item(result)
    except requests.exceptions.TooManyRedirects as err:
        statistics['error_redirects'] += 1
        result = {
            'id': id,
            'url': url,
            'status': 'ОШИБКА ПЕРЕНАПРАВЛЕНИЯ',
            'comment': str(err.args[0]),
            'check_count': check_count,
            'datetime_check': datetime.now()
        }
        report_item(result)


#
#    Функция инициализации и запуска потоков
#    для проверки url
#
def init_threads(urls):
    log_stdout(f'Инициализация потоков')
    threads = []
    i = 0  # счетчик процессов

    for index, url in enumerate(urls):
        # Если включен дебаг и сработал лимит, то запускаем потоки
        # на выполнение
        if config['DEBUG'] == '1' and index == config['DEBUG_LIMIT']:
            break

        if i <= config['WORKERS']:
            i += 1  # инкрементируем счетчик активных процессов

            # Инициализация потоков
            threads.append(
                threading.Thread(
                    target=check_endpoint,
                    args=(index, url, )
                )
            )
        # Если число процессов больше WORKERS или конец списка,
        # то запускаем на выполнение
        if i == config['WORKERS']:
            log_stdout(f'Запуск потоков {index}')
            # Запускаем потоки на выполнение
            for thread in threads:
                thread.start()

            log_stdout('Ожидание завершения')
            # Ожидаем завершения выполения потоков
            for thread in threads:
                thread.join()

            # очищаем переменные после выполнения потоков
            i = 0
            threads = []

    # Запускаем оставшиеся потоки на выполнение
    for thread in threads:
        thread.start()

    log_stdout('Завершение потоков')
    # Ожидаем завершения выполения потоков
    for thread in threads:
        thread.join()

    return


#
#   Инициализация глобальных переменных
#

# Парсим аргументы
parser = argparse.ArgumentParser()
parser.add_argument(
    "-d",
    "--debug",
    help="enable debug",
    action="store_true"
)
parser.add_argument(
    "-c",
    "--config",
    help="config file (default: .env)"
)
parser.add_argument(
    "-f",
    "--file",
    help="filename with url/domain/ip list"
)
parser.add_argument(
    "-r",
    "--response",
    help="response url from blocked page"
)
args = parser.parse_args()

# Загружаем параметры config
if args.config:
    config = dotenv_values(args.config)
else:
    config = dotenv_values('.env')

# Проверка и форматирование config
check_config(config, args)

logpath = config['REPORT_FILE']
logger = logging.getLogger('log')
logger.setLevel(logging.INFO)
ch = logging.FileHandler(logpath)
ch.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(ch)

# Статистика по проверке
statistics = {
    'all': 0,
    'blocked': 0,
    'not_blocked': 0,
    'error_connection': 0,
    'error_read': 0,
    'error_peer': 0,
    'error_url': 0,
    'error_redirects': 0,
    'unknown': 0
}


#
#   main
#
def main():
    # Подключаем глобальную переменную для подсчета статистики
    global statistics

    # Загружаем новый список url.list
    if config['FTP_ENABLE'] == '1':
        ftp_download()

    # Фиксируем время начала проверки
    START_TIME = datetime.now()

    # Открываем файл со списком urlов
    try:
        fd_in = open(config['FILENAME'], 'r')
    except OSError:
        log_stdout(f'Невозможно открыть или прочитать файл: \
{config["FILENAME"]}')
        sys.exit()

    # Пишем в лог проверок первую строку
    log_stdout(f'Инициализация отчета')
    logger.info(f'id|url|status|comment|check_count|datetime_check')

#     # Открываем файл для записи отчета
#     try:
#         fd_out = open(config['REPORT_FILE'], 'w')
#     except OSError:
#         log_stdout(f'Невозможно открыть или прочитать файл: \
# {config["REPORT_FILE"]}')
#         sys.exit()

    # Инициализация потоков
    init_threads(fd_in)

    # # Закрываем файл с отчетом
    # fd_out.close()
    log_stdout(f'Сохранение отчета в файл {config["REPORT_FILE"]}')

    # Определяем время окончания проверки
    END_TIME = datetime.now()

    # Отправляем файл на FTP
    if config['FTP_ENABLE'] == '1' and config['FTP_UPLOAD'] == '1':
        ftp_upload()

    # Если включен параметр SMTP_ENABLE
    if config['SMTP_ENABLE'] == '1':
        # Отправляем email с отчетом и статистикой
        send_report(f'''
Начало проверки: {START_TIME}
Окончание проверки: {END_TIME}
Проверка заняла: {END_TIME - START_TIME}

Всего проверено: {statistics["all"]}
Заблокировано: {statistics["blocked"]}
НЕ ЗАБЛОКИРОВАНО: {statistics["not_blocked"]}
Ошибки соединения: {statistics["error_connection"]}
Ошибки чтения потока: {statistics["error_read"]}
Ошибка пира: {statistics["error_peer"]}
Ошибка url: {statistics["error_url"]}
Ошибка перенаправления: {statistics["error_redirects"]}
Неизвестные ошибки: {statistics["unknown"]}

Файл с отчетом проверки: {config["REPORT_FILE"]}

reponse.url: {config["BLOCK_DOMAIN"]}
        ''', config['REPORT_FILE'])


if __name__ == '__main__':
    main()
