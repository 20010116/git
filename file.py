import datetime
import os
import re
import warnings

import pandas as pd

warnings.filterwarnings('ignore')
from datetime import datetime
import numpy as np
import xlrd

# 天猫保证金上月余额
tmall_margin_details = eval(input(f'请输入{datetime.now().year}年{datetime.now().month - 3}月末余额--天猫保证金：'))

# 直通车上月余额
promote_through_trains = eval(input(f'请输入{datetime.now().year}年{datetime.now().month - 3}月末余额--直通车余额：'))
# 上个月订单路径
# last_month=input('请输入上个月订单路径：')

path = f'{os.getcwd()}'
shops_name = os.path.basename(path)
for i in os.listdir(path):
    # 特殊单------这里先用总特殊单，考虑先跑几家店铺
    if '特殊单' in i:
        special_doc = i
    # 发货汇总
    elif '销售主题分析' in i:
        summary_order = i
    # 核对月份支付宝流水路径
    elif '_' in i and (i.split('_')[-2] == f'{datetime.now().year}0{datetime.now().month - 2}'):
        current_month_water = i
    # 核对月份+1支付宝流水路径
    elif '_' in i and i.split('_')[-2] == f'{datetime.now().year}0{datetime.now().month - 1}':
        next_month_water = i
    # 退货单路径
    elif '售后单' in i:
        return_order = i
    # 上个月订单路径
    elif f'{datetime.now().month - 3}月' in i:
        last_month_order = i
    # 直通车路径
    elif '直通车' in i:
        car_path = i
    # 天猫保证金路径
    elif '天猫保证金' in i:
        tmall_order = i
    else:
        continue



# 日期转换器

def time_conversion(df_value):
    # 定义基准日期
    base_date = pd.to_datetime('1899-12-30')

    # 检查是否为字符串类型，并包含 '-' 符号
    if isinstance(df_value, str) and '-' in df_value:
        return pd.to_datetime(df_value, format='%Y-%m-%d %H:%M:%S').date()
    else:
        # 如果是整数类型，则认为是从 base_date 开始的天数，计算具体的日期
        return base_date + pd.to_timedelta(int(df_value), unit='D')


# 无订单号确认期限
def order_month(df):
    for index, row in df.iterrows():
        if row['订单号'] == '无订单号':
            df.at[index, '订单期限'] = f'{datetime.now().month - 2}月订单'

    return df


# 手工处理特殊单
# special_doc_table = pd.read_excel(os.path.join(path, special_doc),engine='openpyxl')
# special_doc_table = pd.read_excel(os.path.join(path, special_doc),engine='openpyxl')
special_doc_table=pd.read_excel(os.path.join(path,special_doc),engine='openpyxl')
special_doc_table.订单编号 = special_doc_table.订单编号.astype(str)

### 处理发货表

delivery_table = pd.read_excel(os.path.join(path, summary_order))

delivery_table_summary = delivery_table[
    ['原始线上订单号', '付款日期', '发货日期', '订单类型', '标记多标签', '买家账号', '线上商品名', '商品编码',
     '款式编码', '快递公司', '快递单号', '销售数量'
        , '实发数量', '销售金额', '已付金额']]

delivery_table_summary.原始线上订单号 = delivery_table_summary.原始线上订单号.astype(str)


# 处理原始订单号
def order_g(df):
    if '-' in df:
        return df.split('-')[1]
    else:
        return df


delivery_table_summary['原始线上订单号'] = delivery_table_summary['原始线上订单号'].apply(order_g)
# 暂不考虑换补发订单

delivery_table_summary = delivery_table_summary[
    ~delivery_table_summary['订单类型'].str.contains('换货订单|补发订单')
]

### 判断是否特殊单

delivery_table_summary['辅助列'] = delivery_table_summary['原始线上订单号'].apply(
    lambda x: '特殊单' if x in special_doc_table['订单编号'].values else ''
)

delivery_table_summary['入账金额'] = delivery_table_summary['销售金额']


# 加一个原始线上订单号小于19，入账金额直接清零
def calculate_account_amount(row):
    if len(row['原始线上订单号']) < 19:
        return 0
    else:
        if row['辅助列'] == '特殊单':
            if row['实发数量'] == 0:
                return row['销售金额']
            else:
                return row['销售金额'] * 2
        else:
            if row['实发数量'] == 0:
                if '分销' in row['订单类型']:
                    return row['销售金额']
                else:
                    return 0
            else:
                if '无需物流' in row['快递公司'] or '现场取货' in row['快递公司']:
                    return 0
                else:
                    return row['销售金额']


delivery_table_summary['入账金额'] = delivery_table_summary.apply(calculate_account_amount, axis=1)

# 读取上个月订单
last_month_order_table = pd.read_excel(os.path.join(path, last_month_order), sheet_name='聚水潭发货')
# 核对月份流水

check_month_running_water = pd.read_csv(os.path.join(path, current_month_water), header=4, encoding='gbk')

check_month_running_water.dropna(thresh=check_month_running_water.shape[1] / 2, inplace=True)


# R-备注
# S-业务描述
# Q-业务类型
# 定义逻辑函数
def classify(row):
    if "直通车" in row['备注']:
        return "直通车充值"
    elif "超级推荐" in row['备注']:
        return "超级推荐充值"
    elif "淘宝客" in row['备注']:
        return "淘宝客佣金"
    elif "品销宝" in row['备注']:
        return "品销宝充值"
    elif "天猫保证金-解冻" in row['备注']:
        return "天猫保证金-解冻"
    elif "交易退款" in row['业务描述'] or "保证金退款" in row['备注']:
        return "售后退款"
    elif "天猫保证金-充值" in row['备注']:
        return "天猫保证金-充值"
    elif "延迟发货" in row['备注'] or "未按时开具发票" in row['备注']:
        return "平台罚款"
    elif "网商贷-还款" in row['备注']:
        return "网商贷-还款"
    elif "网商贷放款扣费" in row['备注']:
        return "提现扣费"
    elif "技术服务费年费" in row['备注'] or "技术年费年度结算" in row['备注']:
        return "技术服务费年费"
    elif any(substring in row['备注'] for substring in
             ["花呗支付服务费", "花呗分期服务费", "花呗分期免息营销", "花呗分期-退款退费"]):
        return "支付宝服务费"
    elif "信用卡" in row['备注']:
        return "支付宝服务费"
    elif "天猫佣金" in row['备注']:
        return "天猫佣金"
    elif "退回积分" in row['备注'] or "代扣返点积分" in row['备注']:
        return "天猫返点积分"
    elif "品牌新享" in row['备注']:
        return "品牌新享"
    elif "公益宝贝捐" in row['备注']:
        return "公益捐助"
    elif "退货邮费" in row['备注'] or "记账本转账" in row['业务描述']:
        return "售后费用"
    elif "保险承保-卖家版运费险" in row['备注'] or "退货险保费收取" in row['备注']:
        return "平台运费险"
    elif "提现" in row['业务类型']:
        return "提现"
    elif "交易收款" in row['业务描述'] or "海外退货险理赔款" in row['备注'] or "基金代发任务" in row['备注']:
        return "销售收入"
    elif "红包" in row['备注']:
        return "现金红包"
    elif "余利宝-基金申购" in row['备注']:
        return "余利宝-基金申购"
    elif "余利宝-基金赎回" in row['备注']:
        return "余利宝-基金赎回"
    elif "转出到网商银行" in row['备注']:
        return "转账支出-网商银行"
    elif "软件服务费" in row['备注'] or "供应链管理服务费" in row['备注'] or "先用后付技术服务费" in row['备注']:
        return "平台服务费"
    elif "结息" in row['业务类型']:
        return "财务手续费"
    elif row['收入金额（+元）'] == 0:
        return "其他支出"
    else:
        return "其他收入"


# 应用自定义函数到数据框中的每一行
check_month_running_water['费用类型'] = check_month_running_water.apply(classify, axis=1)

# 加个判断
a_list = ['品牌新享', '售后费用', '售后退款', '天猫佣金', '天猫保证金-充值', '天猫保证金-解冻', '天猫返点积分',
          '平台服务费', '平台运费险', '提现', '支付宝服务费', '销售收入']
# 检查哪些费用类型不在列表中
not_in_list = check_month_running_water[~check_month_running_water['费用类型'].isin(a_list)]

# 如果有不在列表中的费用类型，打印出来并给出提示
if not not_in_list.empty:
    print("以下费用类型不在设定的列表中：")
    print(not_in_list['费用类型'].tolist())
else:
    print("所有费用类型都在设定的列表中。")

#  发生时间
check_month_running_water['发生时间'] = pd.to_datetime(check_month_running_water['发生时间'])


# 订单时间
# 定义条件逻辑函数
def apply_conditions(row):
    if '天猫保证金-充值' in str(row['备注']):
        return str(row['业务流水号'])[:6]
    elif '账房' in str(row['业务账单来源']):
        return str(row['业务流水号'])[2:8]
    else:
        return str(row['业务流水号'])[:6]


check_month_running_water['订单时间'] = check_month_running_water.apply(apply_conditions, axis=1)


# R-备注
# A-分类
# M-业务流水号
# U-业务基础订单号
# I-商户订单号
# 定义函数处理每一行数据
def process_row(row):
    if '海外' in row['备注']:
        return row['备注'][-20:-1]
    elif '基金代发任务' in row['备注']:
        return row['备注'][21:40]
    elif row['费用类型'] == '销售收入':
        if row['业务流水号'] == 0:
            return row['备注'][row['备注'].find('P') + 1:]
        else:
            return row['业务基础订单号']
    elif row['费用类型'] == '天猫佣金':
        return row['业务基础订单号'][:19]
    elif row['费用类型'] == '平台服务费':
        return row['商户订单号'][row['商户订单号'].find('P') + 1:]
    elif row['费用类型'] == '天猫保证金-解冻':
        if '天猫保证金-解冻' in row['备注']:
            return row['业务基础订单号'][:19]
        elif '{' in row['备注']:
            return row['备注'][row['备注'].find('{') + 1:row['备注'].find('}')]
        else:
            return row['备注'][row['备注'].find('(') + 1:row['备注'].find(')')]
    elif row['费用类型'] == '聚划算佣金':
        if '(' in row['备注']:
            return row['备注'][row['备注'].find('(') + 1:row['备注'].find(')')]
        elif '{' in row['备注']:
            return row['备注'][row['备注'].find('{') + 1:row['备注'].find('}')]
    elif row['费用类型'] == '天猫返点积分' or row['费用类型'] == '支付宝服务费':
        return row['业务基础订单号'][:19]
    elif row['费用类型'] == '淘宝客佣金':
        return row['备注'][row['备注'].find('[') + 1:row['备注'].find(']')]
    elif row['费用类型'] == '平台运费险':
        return row['业务基础订单号'][:19]
    elif row['费用类型'] == '公益捐助':
        return row['商户订单号'][row['商户订单号'].find('_', row['商户订单号'].find('_') + 1) + 1:]
    elif row['费用类型'] == '花呗服务费':
        return row['备注'][49:68]
    elif '品牌新享' in row['费用类型']:
        #         直接取备注里面的第二个括号里面的数字
        match = re.search(r'\((\d{19})\)', row['备注'])
        if match:
            return match.group(1)
        else:
            return row['商户订单号'][row['商户订单号'].find('P') + 1:]
    elif '售后退款' in row['费用类型']:
        return row['业务基础订单号'][:19]
    elif '天猫保证金-充值' in row['费用类型']:
        return row['业务基础订单号']
    else:
        return '无订单号'


check_month_running_water['订单号'] = check_month_running_water.apply(process_row, axis=1)

check_month_running_water['订单号'] = check_month_running_water['订单号'].str.strip()

# 金额
check_month_running_water['金额'] = check_month_running_water['收入金额（+元）'] + check_month_running_water[
    '支出金额（-元）']

check_month_running_water_order = check_month_running_water[['费用类型', '订单号', '金额']]
# 匹配是否特殊单
check_month_running_water_order['是否特殊单'] = check_month_running_water_order['订单号'].apply(
    lambda x: '特殊单' if x in special_doc_table['订单编号'].values else ''
)
# 匹配订单期限
check_month_running_water_order['订单期限'] = check_month_running_water_order.订单号.apply(
    lambda x: f'{datetime.now().month - 3}月订单' if x in last_month_order_table['原始线上订单号'].values \
        else (
        f'{datetime.now().month - 2}月订单' if x in delivery_table_summary['原始线上订单号'].values else '未知订单')
)
### 核对月份+1流水

check_next_month_running_water = pd.read_csv(os.path.join(path, next_month_water), header=4, encoding='gbk')

check_next_month_running_water.dropna(thresh=check_next_month_running_water.shape[1] / 2, inplace=True)

# 应用自定义函数到数据框中的每一行
check_next_month_running_water['费用类型'] = check_next_month_running_water.apply(classify, axis=1)

#  发生时间
check_next_month_running_water['发生时间'] = pd.to_datetime(check_next_month_running_water['发生时间'])

check_next_month_running_water['订单时间'] = check_next_month_running_water.apply(apply_conditions, axis=1)

check_next_month_running_water['订单号'] = check_next_month_running_water.apply(process_row, axis=1)

check_next_month_running_water['订单号'] = check_next_month_running_water['订单号'].str.strip()

# 金额
check_next_month_running_water['金额'] = check_next_month_running_water['收入金额（+元）'] + \
                                         check_next_month_running_water['支出金额（-元）']

check_next_month_running_water_order = check_next_month_running_water[['费用类型', '订单号', '金额']]

####  匹配是否为特殊单

check_next_month_running_water_order['是否特殊单'] = check_next_month_running_water_order['订单号'].apply(
    lambda x: '特殊单' if x in special_doc_table['订单编号'].values else ''
)
# 匹配订单期限
check_next_month_running_water_order['订单期限'] = check_next_month_running_water_order.订单号.apply(
    lambda x: f'{datetime.now().month - 3}月订单' if x in last_month_order_table['原始线上订单号'].values \
        else (
        f'{datetime.now().month - 2}月订单' if x in delivery_table_summary['原始线上订单号'].values else '未知订单')
)
check_next_month_running_water_order.sample(1)

# 退货单

return_order = pd.read_excel(os.path.join(path, return_order))

return_order_table = return_order[
    ['线上订单号', '进仓时间', '订单发货时间', '售后分类', '订单支付日期', '售后单号', '买家帐号', '商品编码', '商品名',
     '退货数量', '单价', '类型', '申请金额']]

return_order_table.sample(1)

return_order_table['入账退货金额'] = return_order_table['退货数量'] * return_order_table['单价'] * -1

return_order_table.线上订单号 = return_order_table.线上订单号.astype(str)

return_order_table['是否为特殊单'] = return_order_table['线上订单号'].apply(
    lambda x: '特殊单' if x in special_doc_table['订单编号'].values else ''
)

return_order_table.sample(2)

return_order_table = return_order_table[
    ~return_order_table['售后分类'].str.contains('换货|补发')
]

return_order_table.售后分类.unique()

# 核销汇总

# 发货金额

check_table_order = delivery_table_summary.groupby('原始线上订单号').agg(
    {'入账金额': 'sum'}).reset_index()

check_table_order['是否为特殊单'] = check_table_order['原始线上订单号'].apply(
    lambda x: '特殊单' if x in special_doc_table['订单编号'].values else ''
)

check_table_order['订单期限'] = check_table_order.原始线上订单号.apply(
    lambda x: f'{datetime.now().month - 3}月订单' if x in last_month_order_table['原始线上订单号'].values \
        else (
        f'{datetime.now().month - 2}月订单' if x in delivery_table_summary['原始线上订单号'].values else '未知订单')
)
check_table_order.入账金额.sum()

# 核对月份流水
check_month_salas = \
    check_month_running_water_order[(check_month_running_water_order.费用类型 == '销售收入') & \
                                    (check_month_running_water_order.订单期限 == f'{datetime.now().month - 2}月订单')][
        ['订单号', '金额']]

check_month_refund = \
    check_month_running_water_order[(check_month_running_water_order.费用类型 == '售后退款') & \
                                    (check_month_running_water_order.订单期限 == f'{datetime.now().month - 2}月订单')][
        ['订单号', '金额']]

check_month_refund.金额.sum() + check_month_salas.金额.sum()

# 发货连接---核对月份流水表

check_table = \
    pd.merge(check_table_order, check_month_salas.groupby('订单号').agg({'金额': 'sum'}).reset_index() \
             , how='left', left_on='原始线上订单号', right_on='订单号')

check_table = \
    pd.merge(check_table, check_month_refund.groupby('订单号').agg({'金额': 'sum'}).reset_index() \
             , how='left', left_on='原始线上订单号', right_on='订单号')

check_table.drop(columns=['订单号_x', '订单号_y'], axis=1, inplace=True)

check_table.rename(
    {'金额_x': f'{datetime.now().month - 2}月回款-销售收入', '金额_y': f'{datetime.now().month - 2}月回款-售后退款'},
    axis=1, inplace=True)

check_table.sum()

# 核对月份+1流水筛选
check_next_month_salas = \
    check_next_month_running_water_order[(check_next_month_running_water_order.费用类型 == '销售收入') & \
                                         (
                                                 check_next_month_running_water_order.订单期限 == f'{datetime.now().month - 2}月订单')][
        ['订单号', '金额']]

check_next_month_salas.金额.sum()

check_next_month_refund = \
    check_next_month_running_water_order[(check_next_month_running_water_order.费用类型 == '售后退款') & \
                                         (
                                                 check_next_month_running_water_order.订单期限 == f'{datetime.now().month - 2}月订单')][
        ['订单号', '金额']]

check_next_month_refund.金额.sum()

check_table = \
    pd.merge(check_table, check_next_month_salas.groupby('订单号').agg({'金额': 'sum'}).reset_index()
             , how='left', left_on='原始线上订单号', right_on='订单号')

check_table = \
    pd.merge(check_table, check_next_month_refund.groupby('订单号').agg({'金额': 'sum'}).reset_index()
             , how='left', left_on='原始线上订单号', right_on='订单号')

check_table.drop(columns=['订单号_x', '订单号_y'], axis=1, inplace=True)

check_table.rename(
    {'金额_x': f'{datetime.now().month - 1}月回款-销售收入', '金额_y': f'{datetime.now().month - 1}月回款-售后退款'},
    axis=1, inplace=True)

check_table.sum()

# 核销退货

return_order_table.入账退货金额.sum()

check_table = pd.merge(check_table, return_order_table.groupby('线上订单号').agg({'入账退货金额': 'sum'}).reset_index(),
                       how='left',
                       left_on='原始线上订单号', right_on='线上订单号').copy()
check_table.drop(columns='线上订单号',inplace=True)

check_table.sum()

# 应收差异--条件
for data_key in ['入账金额', f'{datetime.now().month - 2}月回款-销售收入',
                 f'{datetime.now().month - 2}月回款-售后退款', f'{datetime.now().month - 1}月回款-销售收入',
                 f'{datetime.now().month - 1}月回款-售后退款', '入账退货金额']:
    check_table[f'{data_key}'].fillna(0, inplace=True)
check_table['应收差异-条件'] = check_table['入账金额'] - \
                               (check_table[f'{datetime.now().month - 2}月回款-销售收入'] +
                                check_table[f'{datetime.now().month - 2}月回款-售后退款']) - \
                               (check_table[f'{datetime.now().month - 1}月回款-销售收入'] +
                                check_table[f'{datetime.now().month - 1}月回款-售后退款']) + \
                               check_table['入账退货金额']


def only_refund(df):
    # 检查 '应收差异' 列是否存在
    if '应收差异-条件' not in df.columns:
        raise ValueError("DataFrame does not contain '应收差异-条件' column")

    # 仅对应收差异不为0的行应用处理
    # df = df[df['应收差异-条件'] != 0].copy()
    # 初始化 '仅退款' 列
    df['仅退款'] = 0

    # 获取当前月份和前两个月的月份
    month_current = datetime.now().month
    month_previous1 = month_current - 1
    month_previous2 = month_current - 2

    # 计算回款和退款的总和
    df[f'{month_previous1}月回款-销售收入'].fillna(0, inplace=True)
    df[f'{month_previous2}月回款-销售收入'].fillna(0, inplace=True)
    df[f'{month_previous1}月回款-售后退款'].fillna(0, inplace=True)
    df[f'{month_previous2}月回款-售后退款'].fillna(0, inplace=True)

    df['总销售收入'] = df[f'{month_previous1}月回款-销售收入'] + df[f'{month_previous2}月回款-销售收入']
    df['总退款'] = df[f'{month_previous1}月回款-售后退款'] + df[f'{month_previous2}月回款-售后退款']

    # 计算条件
    condition1 = (df['总销售收入'] > 0) & (df['总退款'] != 0)
    condition2 = df['入账退货金额'] < 0
    condition3 = df['入账退货金额'] == 0
    condition4 = (df['总销售收入'] > 0) & (df['总退款'] == 0)

    # 应用条件进行计算
    # (总销售收入 > 0 并且 总退款 != 0) 和 (总退款 > 入账退货金额) 时，仅退款 = 总退款 - 入账退货金额
    df.loc[condition1 & condition2 & (df['总退款'] > df['入账退货金额']), '仅退款'] = df['总退款'] - df['入账退货金额']
    # （总销售收入 > 0 并且 总退款 != 0）和 (入账退货金额 == 0) 时，仅退款 = 总退款
    df.loc[condition1 & condition3, '仅退款'] = df['总退款']
    # 有收入，没有流水退，
    #     df.loc[condition4, '仅退款']=df['入账金额']-df['总销售收入']

    # 删除临时计算列
    df.drop(columns=['总销售收入', '总退款'], inplace=True)
    df.update(df)
    return df


# 将负数修改为正数
check_table[
    [f'{datetime.now().month - 2}月回款-售后退款', f'{datetime.now().month - 1}月回款-售后退款', '入账退货金额']] = \
    check_table[[f'{datetime.now().month - 2}月回款-售后退款', f'{datetime.now().month - 1}月回款-售后退款',
                 '入账退货金额']].abs()

check_table_data = only_refund(check_table)

# 将修改过的负数改回来
check_table_data[
    [f'{datetime.now().month - 2}月回款-售后退款', f'{datetime.now().month - 1}月回款-售后退款', '入账退货金额',
     '仅退款']] = \
    check_table_data[
        [f'{datetime.now().month - 2}月回款-售后退款', f'{datetime.now().month - 1}月回款-售后退款', '入账退货金额',
         '仅退款']].apply(lambda x: -x)
check_table_data['应收差异'] = check_table_data['入账金额'] - \
                               (check_table_data[f'{datetime.now().month - 2}月回款-销售收入'] +
                                check_table_data[f'{datetime.now().month - 2}月回款-售后退款']) - \
                               (check_table_data[f'{datetime.now().month - 1}月回款-销售收入'] +
                                check_table_data[f'{datetime.now().month - 1}月回款-售后退款']) + \
                               check_table_data['入账退货金额'] + check_table_data['仅退款']

# 费用拆解
check_running_water = order_month(check_month_running_water_order)
check_running_water['是否特殊单'].fillna('非特殊单', inplace=True)
check_running_water['是否特殊单'].fillna('非特殊单', inplace=True)
# 特殊单费用详细
special_order_costs = pd.concat([check_running_water[['费用类型', '订单号', '金额', '订单期限', '是否特殊单']],
                                 check_month_running_water_order[check_month_running_water_order.订单期限 == '5月订单'][
                                     ['费用类型', '订单号', '金额', '订单期限', '是否特殊单']]]). \
    pivot_table(values='金额', index='费用类型', columns=['订单期限', '是否特殊单'], aggfunc='sum', margins=True,
                margins_name='总计')

# 时间费用详解
next_order_month = \
    check_next_month_running_water_order[
        check_next_month_running_water_order.订单期限 == f'{datetime.now().month - 2}月订单'][
        ['费用类型', '订单号', '金额', '订单期限', '是否特殊单']]
next_order_month.订单期限 = f'{datetime.now().month - 1}月订单'
time_order_costs = pd.concat([check_running_water[['费用类型', '订单号', '金额', '订单期限', '是否特殊单']],
                              next_order_month]).pivot_table(values='金额', index='费用类型', columns=['订单期限'],
                                                             aggfunc='sum', margins=True, margins_name='总计')
# 针对原始线上订单号为小于19位进行标注
check_table_data['备注'] = check_table_data['原始线上订单号'].apply(lambda x: '店铺拿板' if len(x) < 19 else '')
# 针对店铺拿板，金额全部清0
amount_columns = ['入账金额', f'{datetime.now().month - 2}月回款-销售收入',
                  f'{datetime.now().month - 2}月回款-售后退款', f'{datetime.now().month - 1}月回款-销售收入',
                  f'{datetime.now().month - 1}月回款-售后退款',
                  '入账退货金额', '应收差异-条件', '仅退款', '应收差异']

check_table_data.loc[check_table_data['备注'] == '店铺拿板', amount_columns] = 0
# 筛选未知订单
unknown_order=check_month_running_water_order[(check_month_running_water_order.订单期限=='未知订单')&
                                ((check_month_running_water_order.费用类型=='销售收入')|
                                 (check_month_running_water_order.费用类型=='售后退款'))]
# 拼接未知订单
for index, row in unknown_order.iterrows():
    original_order_id = f"{row['订单号']}{row['订单期限']}{row['是否特殊单']}"
    if row['费用类型'] == '销售收入':
        check_table_data = check_table_data.append({
            '原始线上订单号': original_order_id,
            '入账金额': 0,
            '是否为特殊单': row['是否特殊单'],
            '订单期限': row['订单期限'],
            '5月回款-销售收入': row['金额'],
            '5月回款-售后退款': 0.0,
            '6月回款-销售收入': 0.0,
            '6月回款-售后退款': 0.0,
            '入账退货金额': 0.0,
            '应收差异-条件': 0.0,
            '仅退款': 0.0,
            '应收差异': 0.0
        }, ignore_index=True)
    elif row['费用类型'] == '售后退款':
        check_table_data = check_table_data.append({
            '原始线上订单号': original_order_id,
            '入账金额': 0,
            '是否为特殊单': row['是否特殊单'],
            '订单期限': row['订单期限'],
            '5月回款-销售收入': 0.0,
            '5月回款-售后退款': row['金额'],
            '6月回款-销售收入': 0.0,
            '6月回款-售后退款': 0.0,
            '入账退货金额': 0.0,
            '应收差异-条件': 0.0,
            '仅退款': 0.0,
            '应收差异': 0.0
        }, ignore_index=True)
# 汇总表---发货订单核销

summary_order_check = {
    '发货-销售订单': [delivery_table_summary.入账金额.sum() - delivery_table_summary[
        delivery_table_summary.辅助列 == '特殊单'].入账金额.sum()],
    '发货-特殊单': [delivery_table_summary[delivery_table_summary.辅助列 == '特殊单'].入账金额.sum()],
    '小计': [delivery_table_summary.入账金额.sum() + delivery_table_summary[
        delivery_table_summary.辅助列 == '特殊单'].入账金额.sum()],
    '退款-销售订单': [return_order_table.入账退货金额.sum()],
    '退款-无信息件': [0],
    '退款-仅退款': [0],
    '退款-特殊单': [return_order_table[return_order_table.是否为特殊单 == '特殊单'].入账退货金额.sum()],
    '小计': [delivery_table_summary.入账金额.sum()],
    '应收合计': [delivery_table_summary.入账金额.sum()],
    '回款-本期回款': [check_table[f'{datetime.now().month - 2}月回款-销售收入'].sum() + check_table[
        f'{datetime.now().month - 2}月回款-售后退款'].sum()],
    '回款-本期赔付': [0],
}

summary_order_check_table = pd.DataFrame(summary_order_check)

# summary_order_check_table

# 汇总表--特殊单费用

# special_doc_table

special_doc_table_order = special_doc_table[['平台', '订单编号', '订单日期', '刷单本金', '刷单佣金', '快递费']]

special_doc_table_data = special_doc_table_order[
    special_doc_table_order.订单日期.dt.month == datetime.now().month - 2].groupby('平台'). \
    agg({'刷单本金': 'sum', '刷单佣金': 'sum', '快递费': 'sum'}).reset_index()
special_doc_table_data = pd.concat([special_doc_table_data, special_doc_table_data.sum().to_frame().T])
special_doc_table_data.iloc[-1, 0] = '总计'
special_doc_table_data['小计'] = special_doc_table_data[['刷单本金', '刷单佣金', '快递费']].sum(axis=1)

# special_doc_table_data

# 汇总表----天猫保证金

margin_details = pd.read_csv(os.path.join(path, tmall_order))

margin_details['业务订单号'] = margin_details['业务订单号'][2:19]


def check_conditions(row):
    if '违规违约金' in row['业务描述']:
        return '违规违约金（保证金扣款）'
    elif '充值' in row['原因']:
        return '充值'
    elif '交易赔付' in row['原因']:
        return '交易赔付（保证金扣款）'
    elif '售后退款' in row['原因']:
        return '售后退款（保证金退款）'
    else:
        return '售后费用'


margin_details['费用项目'] = margin_details.apply(check_conditions, axis=1)

margin_details.columns

margin_details_order = margin_details[
    ['业务订单号', '费用项目', '金额(元)', '时间', '原因', '来源账户', '去向账户', '备注', '业务描述', '订单id/处罚id',
     '资金组成']]

margin_details_order.groupby('费用项目').agg({'金额(元)': 'sum'}).reset_index()

margin_details_order[margin_details_order.费用项目 == '充值']['金额(元)'].sum()

data_margin_details = {
    f'{datetime.now().year}年{datetime.now().month - 2}月': [
        f'{datetime.now().year}年{datetime.now().month - 3}月末余额',
        f'{datetime.now().year}年{datetime.now().month - 2}月末余额', '本月充值', '充值', '本月支出',
        '交易赔付（保证金扣款）', '违规违约金（保证金扣款）', '售后退款（保证金退款）', '售后费用', '试算平衡'],
    '天猫保证金明细': [f'{tmall_margin_details}', 0, 0, 0, 0, 0, 0, 0, 0, 0]  # 2024年3月末余额——————进一步确认来源
}

data_margin_details_table = pd.DataFrame(data_margin_details)
data_margin_details_table.天猫保证金明细=data_margin_details_table.天猫保证金明细.astype(float)
# 充值
data_margin_details_table.loc[
    data_margin_details_table[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '充值', '天猫保证金明细'] = \
    margin_details_order[margin_details_order.费用项目 == '充值']['金额(元)'].sum()
# 交易赔付（保证金扣款）
data_margin_details_table.loc[data_margin_details_table[
                                  f'{datetime.now().year}年{datetime.now().month - 2}月'] == '交易赔付（保证金扣款）', '天猫保证金明细'] = \
    margin_details_order[margin_details_order.费用项目 == '交易赔付（保证金扣款）']['金额(元)'].sum()
# 违规违约金（保证金扣款）
data_margin_details_table.loc[data_margin_details_table[
                                  f'{datetime.now().year}年{datetime.now().month - 2}月'] == '违规违约金（保证金扣款）', '天猫保证金明细'] = \
    margin_details_order[margin_details_order.费用项目 == '违规违约金（保证金扣款）']['金额(元)'].sum()
# 售后退款（保证金退款）
data_margin_details_table.loc[data_margin_details_table[
                                  f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后退款（保证金退款）', '天猫保证金明细'] = \
    margin_details_order[margin_details_order.费用项目 == '售后退款（保证金退款）']['金额(元)'].sum()
# 售后费用
data_margin_details_table.loc[
    data_margin_details_table[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后费用', '天猫保证金明细'] = \
    margin_details_order[margin_details_order.费用项目 == '售后费用']['金额(元)'].sum()
# 本月充值
data_margin_details_table.loc[
    data_margin_details_table[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月充值', '天猫保证金明细'] = \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == '充值', '天猫保证金明细'].values[
        0]
# 本月支出
data_margin_details_table.loc[
    data_margin_details_table[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月支出', '天猫保证金明细'] = \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == '违规违约金（保证金扣款）', '天猫保证金明细'].values[
        0] + \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == '交易赔付（保证金扣款）', '天猫保证金明细'].values[
        0] + \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后退款（保证金退款）', '天猫保证金明细'].values[
        0] + \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后费用', '天猫保证金明细'].values[
        0]
# f'{datetime.now().year}年{datetime.now().month-2}月末余额'计算

data_margin_details_table.loc[data_margin_details_table[
                                  f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 2}月末余额', '天猫保证金明细'] = \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 3}月末余额', '天猫保证金明细'].values[
        0] + \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月充值', '天猫保证金明细'].values[
        0] + \
    data_margin_details_table.loc[data_margin_details_table[
                                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月支出', '天猫保证金明细'].values[
        0]
# f'{datetime.now().year}年{datetime.now().month-3}月末余额'计算
# data_margin_details_table.loc[data_margin_details_table[f'{datetime.now().year}年{datetime.now().month-2}月']==\
#                               f'{datetime.now().year}年{datetime.now().month-3}月末余额','天猫保证金明细']=\

# 试算平衡:四月末余额-三月末余额-充值-本月支出
data_margin_details_table.loc[
    data_margin_details_table[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '试算平衡', '天猫保证金明细'] = \
    ['无差异' if (data_margin_details_table.loc[data_margin_details_table[
                                                    f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 2}月末余额', '天猫保证金明细'].values[
                      0] - \
                  data_margin_details_table.loc[data_margin_details_table[
                                                    f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 3}月末余额', '天猫保证金明细'].values[
                      0] - \
                  data_margin_details_table.loc[data_margin_details_table[
                                                    f'{datetime.now().year}年{datetime.now().month - 2}月'] == '充值', '天猫保证金明细'].values[
                      0] - \
                  data_margin_details_table.loc[data_margin_details_table[
                                                    f'{datetime.now().year}年{datetime.now().month - 2}月'] == '交易赔付（保证金扣款）', '天猫保证金明细'].values[
                      0] - \
                  data_margin_details_table.loc[data_margin_details_table[
                                                    f'{datetime.now().year}年{datetime.now().month - 2}月'] == '违规违约金（保证金扣款）', '天猫保证金明细'].values[
                      0] - \
                  data_margin_details_table.loc[data_margin_details_table[
                                                    f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后退款（保证金退款）', '天猫保证金明细'].values[
                      0] - \
                  data_margin_details_table.loc[data_margin_details_table[
                                                    f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后费用', '天猫保证金明细'].values[
                      0]) < 1 else '有差异']

data_margin_details_table

# 汇总表----天猫账单数据汇总

check_month_running_water['辅助列'] = check_month_running_water['订单号'].apply(
    lambda x: '特殊单' if x in special_doc_table['订单编号'].values else ''
)

check_month_running_water[check_month_running_water.辅助列 == '特殊单'].shape

check_month_running_water_summary = \
    check_month_running_water[
        ['订单号', '发生时间', '金额', '辅助列', '费用类型', '收入金额（+元）', '支出金额（-元）', '账户余额（元）']]

# 交易收款
tmall_billing_data = {
    f'{datetime.now().year}年{datetime.now().month - 2}月': [
        f'{datetime.now().year}年{datetime.now().month - 3}月末余额',
        f'{datetime.now().year}年{datetime.now().month - 2}月末余额',
        '（一）交易收款',
        '销售收入',
        '特殊单',
        '售后退款',
        '现金红包',
        '（二）销售费用',
        '天猫佣金',
        '天猫返点积分',
        '支付宝服务费',
        '平台运费险',
        '特殊单-天猫佣金',
        '特殊单-天猫返点积分',
        '特殊单-支付宝服务费',
        '特殊单-平台运费险',
        '特殊单-品牌新享',
        '公益捐助',
        '财务手续费',
        '品牌新享',
        '平台服务费',
        '售后费用',
        '淘宝客佣金',
        ' ',
        '平台年费',
        ' ',
        '（三）推广账户充值',
        '直通车充值',
        '钻展充值',
        '超级推荐充值',
        '品销报充值',
        ' ',
        '（四）待确认项',
        '其他收入',
        '其他支出',
        '（五）资金调拨',
        '网商贷-放款',
        '网商贷-还款',
        '提现',
        '转账支出-网商银行',
        '天猫保证金-充值',
        '天猫保证金-解冻',
        '余利宝-基金申购',
        '余利宝-基金赎回',
        '（六）试算平衡',
        '总计',
        '试算平衡'
    ],
    '支付宝账务明细': [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                       0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
}

tmall_billing_data = pd.DataFrame(tmall_billing_data)

tmall_billing_data

check_month_running_water_summary.sample(1)

####  2024年f{datetime.now().month-3}月末余额:

tmall_billing_data.loc[tmall_billing_data[
                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 3}月末余额', '支付宝账务明细'] = \
    check_month_running_water_summary[
        check_month_running_water_summary.发生时间 == min(check_month_running_water_summary.发生时间)][
        '账户余额（元）'].values[0] \
    - check_month_running_water_summary[
        check_month_running_water_summary.发生时间 == min(check_month_running_water_summary.发生时间)][
        '支出金额（-元）'].values[0] \
    - check_month_running_water_summary[
        check_month_running_water_summary.发生时间 == min(check_month_running_water_summary.发生时间)][
        '收入金额（+元）'].values[0]

#### （一）交易收款

# 销售收入
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '销售收入', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 != '特殊单') & (
            check_month_running_water_summary.费用类型 == '销售收入')].金额.sum()

# 特殊单
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 == '特殊单') & (
            check_month_running_water_summary.费用类型 == '销售收入')].金额.sum()

# 售后退款
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后退款', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 != '特殊单') & (
            check_month_running_water_summary.费用类型 == '售后退款')].金额.sum()

# 现金红包
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '现金红包', '支付宝账务明细'] = \
    check_month_running_water_summary[check_month_running_water_summary.费用类型 == '现金红包'].金额.sum()

#### （二）销售费用

# 天猫佣金
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫佣金', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 != '特殊单') & (
            check_month_running_water_summary.费用类型 == '天猫佣金')].金额.sum()

# 天猫返点积分
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫返点积分', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 != '特殊单') & (
            check_month_running_water_summary.费用类型 == '天猫返点积分')].金额.sum()

# 支付宝服务费
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '支付宝服务费', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 != '特殊单') & (
            check_month_running_water_summary.费用类型 == '支付宝服务费')].金额.sum()

# 平台运费险
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '平台运费险', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 != '特殊单') & (
            check_month_running_water_summary.费用类型 == '平台运费险')].金额.sum()

# 特殊单-天猫佣金
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-天猫佣金', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 == '特殊单') & (
            check_month_running_water_summary.费用类型 == '天猫佣金')].金额.sum()

# 特殊单-天猫返点积分
tmall_billing_data.loc[tmall_billing_data[
                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-天猫返点积分', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 == '特殊单') & (
            check_month_running_water_summary.费用类型 == '天猫返点积分')].金额.sum()

# 特殊单-支付宝服务费
tmall_billing_data.loc[tmall_billing_data[
                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-支付宝服务费', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 == '特殊单') & (
            check_month_running_water_summary.费用类型 == '支付宝服务费')].金额.sum()

# 特殊单-平台运费险
tmall_billing_data.loc[tmall_billing_data[
                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-平台运费险', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 == '特殊单') & (
            check_month_running_water_summary.费用类型 == '平台运费险')].金额.sum()

# 特殊单-品牌新享
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-品牌新享', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 == '特殊单') & (
            check_month_running_water_summary.费用类型 == '品牌新享')].金额.sum()

# 公益捐助
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '公益捐助', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '公益捐助')].金额.sum()

# 财务手续费
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '财务手续费', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '财务手续费')].金额.sum()

# 品牌新享
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '品牌新享', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.辅助列 != '特殊单') & (
            check_month_running_water_summary.费用类型 == '品牌新享')].金额.sum()

# 平台服务费
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '平台服务费', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '平台服务费')].金额.sum()

# 售后费用
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后费用', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '售后费用')].金额.sum()

# 淘宝客佣金
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '淘宝客佣金', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '淘宝客佣金')].金额.sum()

# 平台年费
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '平台年费', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '平台年费')].金额.sum()

#### （三）推广账户充值

# 直通车充值
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '直通车充值', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '直通车充值')].金额.sum()

# 钻展充值
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '钻展充值', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '钻展充值')].金额.sum()

# 超级推荐充值
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '超级推荐充值', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '超级推荐充值')].金额.sum()

# 品销宝充值
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '品销宝充值', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '品销宝充值')].金额.sum()

#### （四）待确认项

# 其他收入
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '其他收入', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '其他收入')].金额.sum()

# 其他支出
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '其他支出', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '其他支出')].金额.sum()

#### （五）资金调拨

# 网商贷-放款
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '网商贷-放款', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '网商贷-放款')].金额.sum()

# 网商贷-还款
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '网商贷-还款', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '网商贷-还款')].金额.sum()

# 提现
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '提现', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '提现')].金额.sum()

# 转账支出-网商银行
tmall_billing_data.loc[tmall_billing_data[
                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == '转账支出-网商银行', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '转账支出-网商银行')].金额.sum()

# 天猫保证金-充值
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫保证金-充值', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '天猫保证金-充值')].金额.sum()

# 天猫保证金-解冻
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫保证金-解冻', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '天猫保证金-解冻')].金额.sum()

# 余利宝-基金申购
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '余利宝-基金申购', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '余利宝-基金申购')].金额.sum()

# 余利宝-基金赎回
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '余利宝-基金赎回', '支付宝账务明细'] = \
    check_month_running_water_summary[(check_month_running_water_summary.费用类型 == '余利宝-基金赎回')].金额.sum()

# （一）交易收款
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（一）交易收款', '支付宝账务明细'] = \
    tmall_billing_data.loc[tmall_billing_data[
                               f'{datetime.now().year}年{datetime.now().month - 2}月'] == '销售收入', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后退款', '支付宝账务明细'].values[
        0]

# （二）销售费用
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（二）销售费用', '支付宝账务明细'] = \
    tmall_billing_data.loc[tmall_billing_data[
                               f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫佣金', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫返点积分', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '支付宝服务费', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '平台运费险', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-天猫佣金', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-天猫返点积分', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-支付宝服务费', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-平台运费险', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '特殊单-品牌新享', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '公益捐助', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '财务手续费', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '品牌新享', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '平台服务费', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '售后费用', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '淘宝客佣金', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '平台年费', '支付宝账务明细'].values[
        0]


# 检查每个条件行是否存在且非空
def get_value(dataframe, condition):
    if dataframe.loc[
        dataframe[f'{datetime.now().year}年{datetime.now().month - 2}月'] == condition, '支付宝账务明细'].empty:
        return 0
    else:
        return dataframe.loc[
            dataframe[f'{datetime.now().year}年{datetime.now().month - 2}月'] == condition, '支付宝账务明细'].values[0]


tmall_billing_data.loc[tmall_billing_data[
                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（三）推广账户充值', '支付宝账务明细'] = \
    get_value(tmall_billing_data, '直通车充值') + \
    get_value(tmall_billing_data, '钻展充值') + \
    get_value(tmall_billing_data, '超级推荐充值') + \
    get_value(tmall_billing_data, '品销宝充值')

# （四）待确认项
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（四）待确认项', '支付宝账务明细'] = \
    tmall_billing_data.loc[tmall_billing_data[
                               f'{datetime.now().year}年{datetime.now().month - 2}月'] == '其他收入', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '其他支出', '支付宝账务明细'].values[
        0]

# （五）资金调拔
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（五）资金调拨', '支付宝账务明细'] = \
    tmall_billing_data.loc[tmall_billing_data[
                               f'{datetime.now().year}年{datetime.now().month - 2}月'] == '网商贷-放款', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '网商贷-还款', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[
        tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '提现', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '转账支出-网商银行', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫保证金-充值', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '天猫保证金-解冻', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '余利宝-基金申购', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '余利宝-基金赎回', '支付宝账务明细'].values[
        0]

# 总计
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '总计', '支付宝账务明细'] = \
    +tmall_billing_data.loc[tmall_billing_data[
                                f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（一）交易收款', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（二）销售费用', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（三）推广账户充值', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（四）待确认项', '支付宝账务明细'].values[
        0] \
    + tmall_billing_data.loc[tmall_billing_data[
                                 f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（五）资金调拨', '支付宝账务明细'].values[
        0]

#### （六）试算平衡

# 试算平衡
tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '试算平衡', '支付宝账务明细'] = \
    round(round(tmall_billing_data.loc[tmall_billing_data[
                                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == '总计', '支付宝账务明细'].values[
                    0], 2) - \
          round((check_month_running_water_summary['收入金额（+元）'].sum() + check_month_running_water_summary[
              '支出金额（-元）'].sum()), 2), 0)


# （六）试算平衡
def trial_balance(number):
    if number == 0:
        return ' '
    else:
        return '有问题'


tmall_billing_data.loc[
    tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '（六）试算平衡', '支付宝账务明细'] = \
    trial_balance(tmall_billing_data.loc[tmall_billing_data[
                                             f'{datetime.now().year}年{datetime.now().month - 2}月'] == '试算平衡', '支付宝账务明细'].values[
                      0])

# 2024年4月末余额:
tmall_billing_data.loc[tmall_billing_data[
                           f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 2}月末余额', '支付宝账务明细'] = \
    tmall_billing_data.loc[tmall_billing_data[
                               f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 3}月末余额', '支付宝账务明细'].values[
        0] + \
    tmall_billing_data.loc[
        tmall_billing_data[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '总计', '支付宝账务明细'].values[
        0]

# tmall_billing_data

# check_month_running_water[check_month_running_water.辅助列 == '特殊单'].shape

# 天猫店铺-推广账户费用汇总表

through_train = pd.read_csv(os.path.join(path, car_path), encoding='gbk')

through_train.sample(2)

# def split_througn_train(value):
#     if value[0].isdigit():
#         return value[8:]
#     elif value[0]=='支':
#         return value[3:]
#     else:
#         return value

# through_train['备注']=through_train['备注'].apply(split_througn_train)

# through_train.备注.unique()

tmall_express = {
    f'{datetime.now().year}年{datetime.now().month - 2}月': [
        f'{datetime.now().year}年{datetime.now().month - 3}月末余额：',
        f'{datetime.now().year}年{datetime.now().month - 2}月末余额：',
        '本月充值',
        '本月消耗',
        '提现',
        '试算平衡',
    ],
    '直通车': [f'{promote_through_trains}', 0, 0, 0, 0, 0]
}

tmall_express = pd.DataFrame(tmall_express)
tmall_express.直通车=tmall_express.直通车.astype(float)
# 核对月末余额

tmall_express.loc[tmall_express[
                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 2}月末余额：', '直通车'] = \
    tmall_express.loc[tmall_express[
                          f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 3}月末余额：', '直通车'].values[
        0] + \
    tmall_express.loc[
        tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月充值', '直通车'].values[0] - \
    tmall_express.loc[
        tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月消耗', '直通车'].values[0] - \
    tmall_express.loc[tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '提现', '直通车'].values[
        0]

# through_train

# through_train

# tmall_express

# 本月充值

tmall_express.loc[tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月充值', '直通车'] = \
    through_train[through_train.交易类型 == '充值']['操作金额(元)'].sum()

tmall_express.loc[tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月消耗', '直通车'] = \
    through_train[(through_train.交易类型 != '充值') & (through_train.收支类型 == '收入')]['操作金额(元)'].sum() + \
    through_train[(through_train.交易类型 != '充值') & (through_train.收支类型 != '收入')]['操作金额(元)'].sum()

# 提现

# 提现
tmall_express.loc[tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '提现', '直通车'] = \
    through_train[through_train.备注 == '提现']['操作金额(元)'].sum()

#### 核对月末余额

tmall_express.loc[tmall_express[
                      f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 2}月末余额：', '直通车'] = \
    tmall_express.loc[tmall_express[
                          f'{datetime.now().year}年{datetime.now().month - 2}月'] == f'{datetime.now().year}年{datetime.now().month - 3}月末余额：', '直通车'].values[
        0] + \
    tmall_express.loc[
        tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月充值', '直通车'].values[0] - \
    tmall_express.loc[
        tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '本月消耗', '直通车'].values[0] - \
    tmall_express.loc[tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '提现', '直通车'].values[
        0]


# 检查每个条件行是否存在且非空
def get_values(dataframe, condition):
    if dataframe.loc[dataframe[f'{datetime.now().year}年{datetime.now().month - 2}月'] == condition, '直通车'].empty:
        return 0
    else:
        return \
            dataframe.loc[
                dataframe[f'{datetime.now().year}年{datetime.now().month - 2}月'] == condition, '直通车'].values[
                0]


tmall_express.loc[tmall_express[f'{datetime.now().year}年{datetime.now().month - 2}月'] == '试算平衡', '直通车'] = \
    get_values(tmall_express, f'{datetime.now().year}年{datetime.now().month - 2}月末余额：') - \
    get_values(tmall_express, f'{datetime.now().year}年{datetime.now().month - 3}月末余额：') - \
    get_values(tmall_express, '本月充值') + \
    get_values(tmall_express, '本月消耗')

# tmall_express

# 加工到一个文件夹中
check_table_data
check_table_data = pd.concat([check_table_data.sum().to_frame().T, check_table_data])
check_table_data.iloc[0, [2, -1, 3]] = 0
check_table_data.iloc[0, 0] = '总计'
with pd.ExcelWriter(os.path.join(r'./',
                                 f'{datetime.now().month - 2}月对账-{shops_name}店铺.xlsx'), engine='openpyxl',
                    mode='w') as writer:
    check_table_data.to_excel(writer, sheet_name='核销表', index=False),
    special_order_costs.to_excel(writer, sheet_name='特殊单费用拆解'),
    time_order_costs.to_excel(writer, sheet_name='天猫费用拆解'),
    summary_order_check_table.to_excel(writer, sheet_name='汇总表-发货订单核销', index=False),
    special_doc_table_data.to_excel(writer, sheet_name='汇总表-特殊单费用', index=False),
    data_margin_details_table.to_excel(writer, sheet_name='汇总表-天猫保证金', index=False),
    tmall_billing_data.to_excel(writer, sheet_name='汇总表-天猫账单数据汇总', index=False),
    tmall_express.to_excel(writer, sheet_name='汇总表-推广账户费用', index=False)
print("数据已成功写入Excel文件。")
