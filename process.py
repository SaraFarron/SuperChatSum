import json
import requests
from argparse import ArgumentParser
from datetime import datetime
import os
import glob

arg_parser = ArgumentParser()
arg_parser.add_argument("api_key", help="Currencylayer API Key")
arg_parser.add_argument(
    "input_file", help="JSON file generated by chat-replay-downloader")
arg_parser.add_argument("output_file", help="Output file")
arg_parser.add_argument("-c", help="Currency convertion file",
                        dest="currency_convertion_file", default="currency_convert.json")
arg_parser.add_argument("-t", help="Target Currency. Default TWD.",
                        dest="target_currency", default="TWD")
args = arg_parser.parse_args()

FILE_NAME = args.input_file
OUTPUT_NAME = args.output_file
API_KEY = args.api_key
CURRENCY_CONVERT_FILE = args.currency_convertion_file
EXCHANGE_FILE_PREFIX = "exchange"
TARGET_CURRENCY = args.target_currency


def get_currency_and_amount(s):
    head = s.rstrip('0123456789.,')
    tail = s[len(head):]
    return head.strip(), tail.replace(",", "").strip()

# 獲取匯率，一天更新一次


global __convertion_rates
date = datetime.today().strftime('%Y%m%d')
__convertion_rates_file_name = os.path.join(
    os.path.dirname(__file__),  f"{EXCHANGE_FILE_PREFIX}.{date}.json")

if os.path.isfile(__convertion_rates_file_name):
    with open(__convertion_rates_file_name) as f:
        __convertion_rates = json.load(f)
else:
    for filename in glob.glob(os.path.join(os.path.dirname(__file__), f'{EXCHANGE_FILE_PREFIX}*')):
        os.remove(filename)
    __convertion_rates = requests.get(
        f'http://api.currencylayer.com/live?access_key={API_KEY}').json()["quotes"]
    with open(__convertion_rates_file_name, 'w') as json_file:
        json.dump(__convertion_rates, json_file)


def convert_currency(currency, amount):
    global __convertion_rates
    return amount / __convertion_rates["USD" + currency] * __convertion_rates[f"USD{TARGET_CURRENCY}"]


result = {}
super_chat_max_amounts = {}
super_chat_min_amounts = {}
super_chat_count = 0
super_sticker_count = 0

with open(FILE_NAME) as f:
    datas = json.load(f)

    super_chat_count = len(datas)

    for data in datas:
        if "amount" in data:
            currency, amount = get_currency_and_amount(data['amount'])
            result[currency] = result.get(currency, 0.0) + float(amount)
            if currency not in super_chat_max_amounts or super_chat_max_amounts[currency] < float(amount):
                super_chat_max_amounts[currency] = float(amount)
                # 如果是整數就換成 int 型態
                if super_chat_max_amounts[currency].is_integer():
                    super_chat_max_amounts[currency] = int(super_chat_max_amounts[currency])
            if currency not in super_chat_min_amounts or super_chat_min_amounts[currency] > float(amount):
                super_chat_min_amounts[currency] = float(amount)
                # 如果是整數就換成 int 型態
                if super_chat_min_amounts[currency].is_integer():
                    super_chat_min_amounts[currency] = int(super_chat_max_amounts[currency])
        elif "ticker_duration" in data:
            super_sticker_count += 1

with open(OUTPUT_NAME, 'w', encoding='utf8') as json_file:
    json.dump(result, json_file, ensure_ascii=False)

# 開始貨幣轉換

sum = 0.0
converted_max = {"amount": 0.0, "original_amount": ""}
converted_min = {"amount": float("inf"), "original_amount": ""}

with open(CURRENCY_CONVERT_FILE, encoding='utf8') as f:
    convert_table = json.load(f)

    for currency in result:
        converted_currency = ""
        if currency in convert_table:
            converted_currency = convert_table[currency]
        else:
            converted_currency = currency.replace("$", "D")

        tmp = convert_currency(converted_currency, result[currency])
        sum += tmp

    for currency in super_chat_max_amounts:
        converted_currency = ""
        if currency in convert_table:
            converted_currency = convert_table[currency]
        else:
            converted_currency = currency.replace("$", "D")

        tmp = convert_currency(converted_currency, super_chat_max_amounts[currency])
        if tmp > converted_max["amount"]:
            converted_max["amount"] = tmp
            converted_max["original_amount"] = f"{super_chat_max_amounts[currency]} {converted_currency}"

    for currency in super_chat_min_amounts:
        converted_currency = ""
        if currency in convert_table:
            converted_currency = convert_table[currency]
        else:
            converted_currency = currency.replace("$", "D")

        tmp = convert_currency(converted_currency, super_chat_min_amounts[currency])
        if tmp < converted_min["amount"]:
            converted_min["amount"] = tmp
            converted_min["original_amount"] = f"{super_chat_min_amounts[currency]} {converted_currency}"

    print(f"Total: {'%.4f' % sum} {TARGET_CURRENCY}")
    print(f"{super_chat_count} super chats received.")
    print(f"{super_sticker_count} super stickers received.")
    print("\n")
    print(
        f"Max: {'%.4f' % converted_max['amount']} {TARGET_CURRENCY} ({converted_max['original_amount']})")
    print(
        f"Min: {'%.4f' % converted_min['amount']} {TARGET_CURRENCY} ({converted_min['original_amount']})")