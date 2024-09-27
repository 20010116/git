import pandas as pd
import numpy as np
import warnings

import pymysql

warnings.filterwarnings('ignore')
import os
from datetime import date, datetime, timedelta
import time, random, time
import hashlib
import requests, math
from sqlalchemy import create_engine
import schedule
import time

# df=pd.read_excel(r'C:\Users\Administrator\Desktop\test\基础库表3.xlsx')
# 公共参数和
app_key = '56816c2b55f14196b170d7e98655d852'
app_secret = '299fe008fd6d491f93a1e8b2e7c5b6f7'
access_token = '8f45a1b5d83c43d2abadf01e3c7e6cc6'
headers = {
    "Content-Type": "application/x-www-form-urlencoded;charset=utf-8"
}


# 时间戳函数
def get_timestamp():
    return int(time.time())


# 数字签名
def get_sign(post_data={}):
    list_data = list(post_data.keys())
    sort_data = sorted(list_data)
    string_sign = app_secret

    for k in sort_data:
        if (k == 'sign'):
            continue
        string_sign += str(k)
        string_sign += str(post_data[k])
    sign = hashlib.md5(string_sign.encode('utf-8')).hexdigest()
    return sign


# 普通商品资料查询（按sku）
def query_product(data, delay=1, retries=5):
    url = 'https://openapi.jushuitan.com/open/sku/query'
    req_data = {
        'access_token': access_token,
        'app_key': app_key,
        'timestamp': get_timestamp(),
        'version': 2,
        'charset': 'utf-8',
        'sign': '',
        'biz': str(data)
    }
    req_data['sign'] = get_sign(req_data)
    print(req_data['sign'])

    for attempt in range(retries):
        try:
            response = requests.post(url, headers=headers, data=req_data, verify=False)
            response_data = response.json()

            # Check response status
            if response.status_code == 200 and response_data.get('code') == 0:
                product_list = response_data.get('data', {}).get('datas', [])
                temp = {}

                for product in product_list:
                    if any(sku_id in product.get('sku_id', '') for sku_id in data['sku_ids']):
                        temp = {
                            'i_id': product.get('i_id'),
                            'sku_id': product.get('sku_id'),
                            'name': product.get('name'),
                            'cost_price': product.get('cost_price'),
                            'sale_price': product.get('sale_price'),
                            'market_price': product.get('market_price'),
                            'other_price_1': product.get('other_price_1')
                        }
                        return temp
                print(f'商品id: {data["sku_ids"]}, 未找到匹配的产品！')
                return {}
            else:
                # Handle rate limit errors
                if response_data.get('code') == 199:  # Second-level rate limit
                    print(f'商品id: {data["sku_ids"]}, 秒级调用超频！等待1秒重试...')
                    time.sleep(1)
                elif response_data.get('code') == 200:  # Minute-level rate limit
                    print(f'商品id: {data["sku_ids"]}, 分钟级调用超频！等待60秒重试...')
                    time.sleep(60)
                else:
                    print(
                        f'商品id: {data["sku_ids"]}, 查询失败！响应码: {response_data.get("code")}, 错误信息: {response_data.get("msg")}')
                    return {}

        except requests.exceptions.RequestException as e:
            print(f'请求失败: {e}')
            time.sleep(random.uniform(1, 3))  # Random sleep before retrying

        finally:
            time.sleep(delay)  # 每次请求后等待指定的时间

    print(f'商品id: {data["sku_ids"]}, 重试次数已用尽，返回空结果。')
    return {}


# 开放平台接口频率限制：一秒调用次数最大5次，一分钟调用次数最大100次，如果调用接口报错了，限制一下调用接口的频率
# code199是秒级调用超频，code200是分钟调用超频
# 频率是按照token维度计算的，token之间互相不影响，不同接口也不互相影响 ， 每个接口频率都是单独计算的
# 更新接口
def update_product(data):
    url = 'https://openapi.jushuitan.com/open/jushuitan/itemsku/upload'
    req_data = {
        'access_token': access_token,
        'app_key': app_key,
        'timestamp': get_timestamp(),
        'version': 2,
        'charset': 'utf-8',
        'sign': '',
        'biz': str(data)
    }
    req_data['sign'] = get_sign(req_data)
    print(req_data['sign'])
    time.sleep(random.uniform(0.3, 0.5))
    response = requests.post(url, headers=headers, data=req_data)
    print(response.status_code, response.text)
    if response.status_code == 200 and response.json()['code'] == 0:
        print(f'商品id: {data["items"][0]["sku_id"]}, 更新成功！')
        # return True
    else:
        print(f'商品id: {data["items"][0]["sku_id"]}, 更新失败！')
        # return False


# 定义一个函数来处理裂变款价格-用来更新基础课中的裂变款价格
def process_price(price):
    return price + 3 if price != 0 else 0


# BOM资料查询--BOM维护
def bom_information(data):
    url = 'https://openapi.jushuitan.com/open/webapi/itemapi/bom/getskubompagelist'
    req_data = {
        'access_token': access_token,
        'app_key': app_key,
        'timestamp': get_timestamp(),
        'version': 2,
        'charset': 'utf-8',
        'sign': '',
        'version': 2,
        'biz': str(data)
    }
    req_data['sign'] = get_sign(req_data)
    print(req_data['sign'])
    response = requests.post(url, headers=headers, data=req_data)
    #     print(response.status_code, response.text)
    #     print(response.json())
    if response.status_code == 200 and response.json()['code'] == 0:
        product_list, count_number = response.json()['data'], response.json()['data']['page']['count']
        if 'sku_ids' in req_data['sign']:
            temp = dict()
            for product in product_list:
                if any(sku_id in product['sku_id'] for sku_id in data['sku_ids']):
                    temp = {}
                    for key, value in product.items():
                        if key in ['sku_id', 'i_id', 'name', 'map_name', 'modified']:
                            temp[key] = value  # 保存商品更新需要的字段
            return temp
        else:
            return product_list, count_number
    else:
        print('查询失败！')


# 数据拆解---BOM维护
def new_split_boms(df):
    # 确保 '光版编码' 和 '图案编码' 两列存在，若不存在则创建空列
    df['光版编码'] = df.get('光版编码', '')
    df['图案编码'] = df.get('图案编码', '')

    for index, row in df.iterrows():
        bom_detail = row['BOM明细']
        items = bom_detail.split(',')

        # 初始化光版编码和图案编码
        guangban_codes = []
        tuan_codes = []

        # 遍历所有 items，找到符合条件的光版编码和图案编码
        for item in items:
            item = item.split(',')[0]  # 提取,前的部分
            if ('版' not in item and '图案' in item) or ('图案' in item) or ('元素' in item):
                #                 图案编码
                tuan_codes.append(item)
            #             光版编码
            #             if '版' in item or '图案' not in item and '元素' not in item:
            if ('版' in item) or ('版' in item and '图案' in item) or (
                    '版' not in item and '图案' not in item and '元素' not in item):
                guangban_codes.append(item)

        comma_count = len(items) - 1

        if comma_count == 0:
            # 逗号数量为0
            if tuan_codes:
                df.at[index, '光版编码'] = guangban_codes[0] if guangban_codes else ''
                df.at[index, '图案编码'] = tuan_codes[0] if tuan_codes else ''
            else:
                df.at[index, '光版编码'] = guangban_codes[0] if guangban_codes else ''
                df.at[index, '图案编码'] = tuan_codes[0] if tuan_codes else ''

        elif comma_count == 1:
            # 逗号数量为1
            if tuan_codes:
                df.at[index, '光版编码'] = guangban_codes[0] if guangban_codes else ''
                df.at[index, '图案编码'] = tuan_codes[0] if tuan_codes else ''
            else:
                df.at[index, '光版编码'] = guangban_codes[0] if guangban_codes else ''
                df.at[index, '图案编码'] = tuan_codes[0] if tuan_codes else ''

        elif comma_count in [2, 3, 4]:
            # 逗号数量为2、3或4
            if tuan_codes:
                df.at[index, '光版编码'] = guangban_codes[0] if guangban_codes else ''
                df.at[index, '图案编码'] = '-'.join(tuan_codes)
            else:
                df.at[index, '光版编码'] = guangban_codes[0] if guangban_codes else ''
                df.at[index, '图案编码'] = '-'.join(tuan_codes)
    for index, value in df.iterrows():
        if '版' in value['图案编码']:
            for detail in value['BOM明细'].split(','):
                if ('版' not in detail and '图案' in detail) or ('版' not in detail and '元素' in detail):
                    value['图案编码'] = detail

    return df


# BOM维护-去除*
def pattern_detail(df):
    for index, value in df.iterrows():
        if '版' in value['图案编码']:
            for detail in value['BOM明细'].split(','):
                if ('版' not in detail and '图案' in detail) or ('版' not in detail and '元素' in detail):
                    value['图案编码'] = detail

    return df


# 获取每一天的BOM维护有修改的数据
def get_today(start_time, end_time):
    _, number = bom_information({
        'modified_start': f'{start_time}',
        'modified_end': f'{end_time}',
        "page": {
            "current_page": 1,
            "page_size": 50
        },
    })
    new_bom = []
    total_pages = math.ceil(number / 50)
    for numbers in range(1, math.ceil(number / 50) + 1):
        values = bom_information({
            'modified_start': f'{start_time}',
            'modified_end': f'{end_time}',
            "page": {
                "current_page": f'{numbers}',
                "page_size": 50
            },
        })
        for item in values[0]['list']:
            sku_id = item["sku_id"]
            bom_detail = f'{item["boms"][0]["map_outer_sku_id"]},{item["boms"][1]["map_outer_sku_id"]}'
            modified = item["modified"]  # 修改时间
            new_bom.append([sku_id, bom_detail, modified])
    return pd.DataFrame(new_bom, columns=['商品编码', 'BOM明细', '修改时间'])


# 获取每一天的BOM维护有修改的数据价格
def get_day_money(df):
    for index, row in df.iterrows():
        optical_code = row['光版编码']
        #     product_code=row['商品编码']
        # 光版编码
        #     optical_money=query_product(optical_code)
        optical_money = query_product({
            "sku_ids": f"{optical_code}",
            "page_index": 1,
            "page_size": 50,
        })
        df.at[index, '光版-成本价格'] = optical_money.get('cost_price', 0)
        df.at[index, '光版-销售价格'] = optical_money.get('sale_price', 0)
        df.at[index, '光版-市场价格'] = optical_money.get('market_price', 0)
        df.at[index, '光版-其它价格1'] = optical_money.get('other_price_1', 0)
        df.at[index, '名称'] = optical_money.get('name', 0)
    return df


# 将每日的BOM维护和组合装产品的数据进行备份
def get_mysql(df):
    engine = create_engine("mysql+pymysql://root:123456@localhost:3306/基础库")
    # 将数据写入到数据库中的表 (假设表名为 'your_table')
    try:
        df.to_sql(f'{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d").replace("-0", "-")}-base-library-table',
                  con=engine,
                  if_exists='replace', index=False)
        # df.to_sql(f'{datetime.now().strftime("%Y-%m-%d").replace("-0", "-")}-base-library-table', con=engine,
        #           if_exists='replace', index=False)
        print("数据写入成功！")
    except Exception as e:
        print(f"写入过程中发生错误: {e}")
    # 关闭连接
    engine.dispose()


# 将每日的基础库数据进行备份
def save_to_daily_update_table(df):
    engine = create_engine("mysql+pymysql://root:123456@localhost:3306/每日更新-基础库")
    try:
        # 计算日期
        table_name = f'{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d").replace("-0", "-")}-每日更新-基础库'

        # 将数据写入每日更新的基础库表
        df.to_sql(table_name, con=engine, if_exists='replace', index=False)
        print(f"数据已写入每日更新-基础库中，表名为：{table_name}")
    except Exception as e:
        print(f"写入过程中发生错误: {e}")

    # 关闭连接
    engine.dispose()


# 裂变款的价格维护
def price_computing(df):
    if 'BOM明细' in df.columns:
        df = new_split_boms(df)
        df['光版编码'] = df['光版编码'].str.split('*').str[0]
        df['图案编码'] = df['图案编码'].str.split('*').str[0]
        df = get_day_money(df)
        df['商品-成本价格'] = df['光版-成本价格'].astype(float).apply(process_price)
        df['商品-销售价格'] = df['光版-销售价格'].astype(float).apply(process_price)
        df['商品-市场价格'] = df['光版-市场价格'].astype(float).apply(process_price)
        df['商品-其它价格1'] = df['光版-其它价格1'].astype(float).apply(process_price)
    else:
        df = get_day_money(df)
        df['商品-成本价格'] = df['光版-成本价格'].astype(float).apply(process_price)
        df['商品-销售价格'] = df['光版-销售价格'].astype(float).apply(process_price)
        df['商品-市场价格'] = df['光版-市场价格'].astype(float).apply(process_price)
        df['商品-其它价格1'] = df['光版-其它价格1'].astype(float).apply(process_price)
    return df


# 组合装产品---数据获取接口
def combination_product(data):
    url = r'https://openapi.jushuitan.com/open/combine/sku/query'
    req_data = {
        'access_token': access_token,
        'app_key': app_key,
        'timestamp': get_timestamp(),
        'version': 2,
        'charset': 'utf-8',
        'sign': '',
        'version': 2,
        'biz': str(data)
    }
    req_data['sign'] = get_sign(req_data)
    print(req_data['sign'])
    response = requests.post(url, headers=headers, data=req_data)
    if response.status_code == 200 and response.json()['code'] == 0:
        product_list, count_number = response.json()['data'], response.json()['data']['data_count']
        if 'sku_ids' in req_data['sign']:
            temp = dict()
            for product in product_list:
                if any(sku_id in product['sku_id'] for sku_id in data['sku_ids']):
                    temp = {}
                    for key, value in product.items():
                        if key in ['sku_id', 'i_id', 'name', 'map_name', 'modified']:
                            temp[key] = value  # 保存商品更新需要的字段
            return temp
        else:
            return product_list, count_number
    else:
        print('查询失败！')


# 组合装产品---每日获取
def get_combination_product(start_time, end_time):
    _, number = combination_product({
        "page_index": 1,
        "page_size": 50,
        "modified_begin": f"{start_time}",
        "modified_end": f"{end_time}"
    })
    print(number)
    new_combination = []
    combination_number = math.ceil(number / 50)
    for numbers in range(1, math.ceil(number / 50) + 1):
        values, _ = combination_product({
            "page_index": f'{numbers}',
            "page_size": 50,
            "modified_begin": f"{start_time}",
            "modified_end": f"{end_time}"
        })
        for data in values['datas']:
            if data['sku_qty'] > 1:
                sku_id = data['sku_id']  # 商品编码
                combination_detail = data['enty_sku_id']  # 组合明细
                optical_coding = data['items'][0]['src_sku_id']  # 光板编码
                pattern_style = data['items'][1]['src_sku_id']  # 图案款式
                # name=data['name']                             #名称
                modified = data['modified']  # 修改时间
                order_label = data['labels']  # 商品标签
                new_combination.append(
                    [sku_id, combination_detail, optical_coding, pattern_style, order_label, modified])
            else:
                sku_id = data['sku_id']  # 商品编码
                combination_detail = data['enty_sku_id']  # 组合明细
                optical_coding = data['items'][0]['src_sku_id']  # 光版编码
                pattern_style = np.nan  # 图案款式
                # name=data['name']                             #名称
                order_label = data['labels']  # 商品标签
                modified = data['modified']  # 修改时间
                new_combination.append(
                    [sku_id, combination_detail, optical_coding, pattern_style, order_label, modified])
    return pd.DataFrame(new_combination, columns=['商品编码', '明细', '光版编码', '图案编码', '商品标签', '修改时间'])


# 光版更新函数---针对光版转款
def update_light_version_code(df):
    # 确保'修改时间'是datetime格式
    df['修改时间'] = pd.to_datetime(df['修改时间'], errors='coerce')

    # 确保 '商品编码' 是字符串类型
    df['商品编码'] = df['商品编码'].astype(str)

    # 按商品编码找到最新的修改时间对应的光版编码
    latest_version = df.loc[df.groupby('商品编码')['修改时间'].idxmax()]

    # 将每个商品编码最新的光版编码映射到df的所有行
    df['光版编码'] = df['商品编码'].map(latest_version.set_index('商品编码')['光版编码'])

    return df


# 比对函数
def matching_data(df, new_boms):
    # 遍历new_boms的每一行,
    for number in range(new_boms.shape[0]):
        if new_boms.iloc[number, 0] in df['光版编码'].values:
            if new_boms.iloc[number, 1] not in df['商品编码'].values:
                # 如果光版编码在基础库中但是商品编码不在，添加对应的光版编码和商品编码
                new_entry = {
                    '商品编码': new_boms.iloc[number, 0],
                    '光版编码': new_boms.iloc[number, 1],
                    '图案编码': new_boms.iloc[number, 2],
                    '修改时间': new_boms.iloc[number, 3],
                    '备注': new_boms.iloc[number, 4],
                    '商品标签': new_boms.iloc[number, 5],
                    '光版-成本价格': new_boms.iloc[number, 6],
                    '光版-销售价格': new_boms.iloc[number, 7],
                    '光版-市场价格': new_boms.iloc[number, 8],
                    '光版-其它价格1': new_boms.iloc[number, 9],
                    '名称': new_boms.iloc[number, 10],
                    '商品-成本价格': new_boms.iloc[number, 11],
                    '商品-销售价格': new_boms.iloc[number, 12],
                    '商品-市场价格': new_boms.iloc[number, 13],
                    '商品-其它价格1': new_boms.iloc[number, 14],
                    '明细': new_boms.iloc[number, 15],
                }
                # 将新的数据添加到表格中
                df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        else:
            new_entry = {
                '商品编码': new_boms.iloc[number, 0],
                '光版编码': new_boms.iloc[number, 1],
                '图案编码': new_boms.iloc[number, 2],
                '修改时间': new_boms.iloc[number, 3],
                '备注': new_boms.iloc[number, 4],
                '商品标签': new_boms.iloc[number, 5],
                '光版-成本价格': new_boms.iloc[number, 6],
                '光版-销售价格': new_boms.iloc[number, 7],
                '光版-市场价格': new_boms.iloc[number, 8],
                '光版-其它价格1': new_boms.iloc[number, 9],
                '名称': new_boms.iloc[number, 10],
                '商品-成本价格': new_boms.iloc[number, 11],
                '商品-销售价格': new_boms.iloc[number, 12],
                '商品-市场价格': new_boms.iloc[number, 13],
                '商品-其它价格1': new_boms.iloc[number, 14],
                '明细': new_boms.iloc[number, 15],
            }
            # 将新的数据添加到表格中
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
    return df

# 每日与商品资料的成本价进行比对
def run_check(df):
    for code in df.光版编码.unique():
        test_check_info = {
            "sku_ids": f"{code}",
            "page_index": 1,
            "page_size": 10
        }
        test_check_money = query_product(test_check_info)
        print(test_check_money)
        # print(f'光版编码：{code},成本价为{test_check_money['cost_price']}')
        if len(test_check_money) != 0:
            if df[df.光版编码 == f'{code}']['光版-成本价格'].unique()[0] == test_check_money.get('cost_price', None):
                print(f'{code}价格相同')
            else:
                print(f'{code}价格不同')
                # 进行针对当前裂变款成本价+3的赋值更新
                product_different_code = df[df.光版编码 == f'{code}']
                new_price = test_check_money['cost_price'] + 3
                # 基础库的成本价的更新
                df.loc[df.光版编码 == f'{code}', '光版-成本价格'] = test_check_money.get('cost_price', None)
                df.loc[df.光版编码 == f'{code}', '商品-成本价格'] = test_check_money.get('cost_price', None) + 3
                for _, product in product_different_code.iterrows():
                    product_information=query_product({
                        "sku_ids": product.商品编码,
                    })
                    update_info = {
                        "items": [
                            {
                                "sku_id": product["商品编码"],
                                "i_id": product_information["i_id"],           # 传获取到的i_id,test_check_money['i_id']
                                "c_price": new_price,
                                "name": product_information['name']                   # 传获取到的i_id,test_check_money['name']
                            }
                        ]
                    }
                    print(f'请求到的参数为：{product_information}')
                    print(f'上传接口参数：{update_info}')

                    # update_product(update_info)
    # df.to_excel(r'\\192.168.2.177\财务共享盘\自动化\code_money\基础库表.xlsx',
    #             sheet_name=f'{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}')
    # save_to_daily_update_table(df)
    return df


# 默认查询的是有主料的数据---时间设置
def run_daily_tasks(df):
    # 默认查询的是有主料的数据---时间设置
    start_time = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    end_time = date.today().strftime("%Y-%m-%d")
    # 获取bom数据
    new_boms = get_today(start_time, end_time)
    # 获取组合商品数据
    combination = get_combination_product(start_time, end_time)
    # bom获取价格，组合商品获取价格
    new_boms = price_computing(new_boms)
    combination = price_computing(combination)
    # 增加一列，备注那个渠道
    new_boms['备注'] = 'BOM维护'
    combination['备注'] = '组合装商品及库存'
    # 筛选光版测试的数据
    combination = combination[combination['商品标签'].str.contains('光版测试', na=False)]
    # 合并BOM和组合产品
    new_boms.rename({'BOM明细': '明细'}, axis=1, inplace=True)
    new_boms['商品标签']=np.nan
    new_boms = new_boms[
        ['商品编码', '光版编码', '图案编码', '修改时间', '备注', '商品标签','光版-成本价格', '光版-销售价格',
         '光版-市场价格', '光版-其它价格1', '名称', '商品-成本价格', '商品-销售价格', '商品-市场价格',
         '商品-其它价格1', '明细']]
    combination = combination[
        ['商品编码', '光版编码', '图案编码', '修改时间', '备注', '商品标签', '光版-成本价格', '光版-销售价格',
         '光版-市场价格', '光版-其它价格1', '名称', '商品-成本价格', '商品-销售价格', '商品-市场价格',
         '商品-其它价格1', '明细']]
    # 拼接存入数据库中
    new_daily_data = pd.concat([new_boms, combination])
    # 存入基础库中
    get_mysql(new_daily_data)
    # 将每日数据与基础库中的数据进行比对，
    df = matching_data(df, new_daily_data)
    # 对转款的商品编码进行光版编码的更新----修改时间
    df = update_light_version_code(df)
    save_to_daily_update_table(df)
    run_check(df)
    print("任务运行完毕")

# run_daily_tasks(df)
if __name__ == '__main__':
    # 基础库表--每日从数据库中读取前一天的数据
    # connection = pymysql.connect(
    #     host='localhost',  # 数据库主机
    #     user='root',  # 用户名
    #     password='123456',  # 密码
    #     database='每日更新-基础库',  # 数据库名称
    #     charset='utf8mb4',  # 编码类型
    #     cursorclass=pymysql.cursors.DictCursor
    # )
    # try:
    #     with connection.cursor() as cursor:
    #         cursor.execute("SHOW TABLES")
    #         tables = cursor.fetchall()
    #         previous_day_table_name = f'{(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}-每日更新-基础库'
    #         for table in tables:
    #             table_name=list(table.values())[0]
    #             print(f"检查表名：{table_name}")
    #             if table_name==previous_day_table_name:
    #                 query=f"SELECT * FROM `{table_name}`"
    #                 cursor.execute(query)
    #                 # df=pd.DataFrame(cursor.fetchall(), columns=[desc[0] for desc in cursor.description])
    #                 print(f"成功获取表: {previous_day_table_name}")
    #                 # print(df.columns)
    #                 # print(df.shape)
    #                 break
    #             else:
    #                 print(f'未找到表：{previous_day_table_name}')
    # finally:
    #     connection.close()

    df=pd.read_excel(r'C:\Users\Administrator\Desktop\test\价格测试\单个测试.xlsx')
    run_check(df)
    # run_daily_tasks(df)
# # 每天晚上三点运行任务
#     schedule.every().day.at("03:00").do(run_daily_tasks,df)
#     # 持续运行，检查任务是否需要执行
#     while True:
#         schedule.run_pending()
#         time.sleep(60)  # 等待60秒再检查一次

