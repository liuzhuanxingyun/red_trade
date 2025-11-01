import pandas as pd
import glob
import smtplib
import os
import requests
import zipfile
import plotly.graph_objects as go
import shutil  # 添加此导入

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from tqdm import tqdm
from dotenv import load_dotenv  # 添加此导入

# 在文件顶部加载 .env 文件
load_dotenv()

# 合并数据
def merge_csv_files(symbol='BTCUSDT', interval='15m', directory=None, output_file=None):
    if directory is None:
        directory = f'back_test/data/{symbol}-{interval}/'
    if output_file is None:
        output_file = f'back_test/data/merged_{symbol}-{interval}.csv'
    try:
        csv_files = glob.glob(f'{directory}*.csv')
        if not csv_files:
            raise ValueError(f"目录 {directory} 中未找到 CSV 文件。")
        
        data_frames = []
        for file in csv_files:
            df = pd.read_csv(file, header=0)  # 指定header=0，跳过列名行
            data_frames.append(df)
        
        data = pd.concat(data_frames, ignore_index=True)
        data['open_time'] = pd.to_datetime(data['open_time'], unit='ms')
        data.sort_values('open_time', inplace=True)
        data.to_csv(output_file, index=False)
        print(f"合并完成，保存到 {output_file}，共 {len(data)} 行。")
        return data
    except Exception as e:
        print(f"合并出错：{e}")
        return None

# 按年份和月份合并数据
def merge_csv_files_by_years_months(symbol, interval, years, months, input_dir=None, output_file=None):
    """
    合并指定年月的数据文件为一个新的CSV文件。
    
    参数:
    - symbol: 交易对符号，如 'BTCUSDT'
    - interval: 时间间隔，如 '1m'
    - years: 年份列表，如 [2024, 2025]
    - months: 月份列表，如 [1, 2, 3]
    - input_dir: 输入目录路径，用于获取子文件，如果为None，则使用默认路径 'data/{symbol}-{interval}'
    - output_file: 输出文件路径，如果为None，则使用默认路径 'data/merged_{symbol}-{interval}.csv'
    
    返回:
    - merged_data: 合并后的DataFrame
    """
    
    if input_dir is None:
        input_dir = f'back_test/data/{symbol}-{interval}'
    
    if output_file is None:
        output_file = f'back_test/data/merged_{symbol}-{interval}.csv'
    
    data_frames = []
    
    for year in years:
        for month in months:
            file_path = f'{input_dir}/{symbol}-{interval}-{year}-{month:02d}.csv'
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                data_frames.append(df)
            else:
                print(f"文件不存在: {file_path}")
    
    if data_frames:
        merged_data = pd.concat(data_frames, ignore_index=True)
        # 转换 open_time 为可读格式并排序
        merged_data['open_time'] = pd.to_datetime(merged_data['open_time'], unit='ms')
        merged_data.sort_values('open_time', inplace=True)
        merged_data.to_csv(output_file, index=False)
        print(f"合并完成，输出文件: {output_file}")
        return merged_data
    else:
        print("没有找到任何文件进行合并")
        return pd.DataFrame()

# 加载和处理数据
def load_and_process_data(file_path='back_test/data/merged_BTCUSDT-15m.csv'):

    try:
        data = pd.read_csv(file_path)

        sample_value = str(data['open_time'].iloc[0]) if not data.empty else ''
        if sample_value.isdigit() and len(sample_value) == 13:
            data['open_time'] = pd.to_datetime(data['open_time'], unit='ms')
        else:
            data['open_time'] = pd.to_datetime(data['open_time'])
                
        data.set_index('open_time', inplace=True)
        data = data[['open', 'high', 'low', 'close', 'volume']].rename(
            columns={
                'open': 'Open',
                'high': 'High',
                'low': 'Low',
                'close': 'Close',
                'volume': 'Volume'
            }
        )
        print(f"数据加载和处理完成，共 {len(data)} 行。")
        return data
    except Exception as e:
        print(f"数据加载和处理出错：{e}")
        return None

# 下载Binance数据
def download_binance_data(symbol='ETCUSDT', interval='15m', years=[2020], months=range(1, 13), save_dir='back_test/data'):

    save_dir = f"{save_dir}/{symbol}_{interval}"
    os.makedirs(save_dir, exist_ok=True)
    
    base_url = f"https://data.binance.vision/data/futures/um/monthly/klines/{symbol}/{interval}/"
    
    for year in years:
        for month in months:
            file_name = f"{symbol}-{interval}-{year}-{month:02d}.zip"
            url = base_url + file_name
            save_path = os.path.join(save_dir, file_name)
            
            if os.path.exists(save_path):
                print(f"已存在：{file_name}")
                continue
            
            try:
                print(f"开始下载 {file_name} ...")
                response = requests.get(url, stream=True)
                if response.status_code == 200:
                    total = int(response.headers.get('content-length', 0))
                    with open(save_path, 'wb') as file, tqdm(
                        desc=file_name, total=total, unit='B', unit_scale=True, ncols=100
                    ) as bar:
                        for chunk in response.iter_content(chunk_size=1024):
                            file.write(chunk)
                            bar.update(len(chunk))
                    print(f"✅ 下载完成: {file_name}")
                else:
                    print(f"❌ 无法访问 {file_name} (状态码: {response.status_code})")
            except Exception as e:
                print(f"下载失败 {file_name}: {e}")

# 解压Binance数据
def unzip_binance_data(symbol='ETCUSDT', interval='15m', save_dir='back_test/data'):

    zip_dir = f"{save_dir}/{symbol}_{interval}"
    csv_dir = f"{save_dir}/{symbol}-{interval}"
    os.makedirs(csv_dir, exist_ok=True)
    
    zip_files = glob.glob(f"{zip_dir}/*.zip")
    if not zip_files:
        print(f"未找到zip文件在 {zip_dir}")
        return
    
    for zip_path in zip_files:
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(csv_dir)
            print(f"✅ 解压完成: {os.path.basename(zip_path)}")
        except Exception as e:
            print(f"解压失败 {zip_path}: {e}")

# 发送邮件提醒
def send_email_notification(
    subject,
    body,
    to_email=None,
    from_email=None,
    smtp_server='smtp.qq.com',
    smtp_port=587,
    smtp_user=None,
    smtp_password=None
):
    # 从环境变量读取敏感信息
    if to_email is None:
        to_email = os.getenv('EMAIL_TO')
    if from_email is None:
        from_email = os.getenv('EMAIL_FROM')
    if smtp_user is None:
        smtp_user = os.getenv('SMTP_USER')
    if smtp_password is None:
        smtp_password = os.getenv('SMTP_PASSWORD')
        if smtp_password is None:
            raise ValueError("SMTP_PASSWORD 环境变量未设置，无法发送邮件。")
    
    try:
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_password)
        text = msg.as_string()
        server.sendmail(from_email, to_email, text)
        server.quit()
        print("邮件发送成功。")
    except Exception as e:
        print(f"邮件发送失败：{e}")

def create_3d_heatmap_cube(aggregated, batch_folder, title='3D Heatmap Cube: EMA Period vs ATR Period vs Multiplier'):
    """
    创建并保存 3D 热力图魔方。
    
    参数:
    - aggregated: DataFrame，包含 'ema_period', 'atr_period', 'multiplier', 'win_rate' 列
    - batch_folder: str，保存文件夹路径
    - title: str，图表标题
    """
    try:
        # 创建 3D 散点图（热力图魔方）
        fig = go.Figure(data=[go.Scatter3d(
            x=aggregated['ema_period'],
            y=aggregated['atr_period'],
            z=aggregated['multiplier'],
            mode='markers',
            marker=dict(
                size=5,
                color=aggregated['win_rate'],  # 颜色表示胜率
                colorscale='Viridis',  # 颜色尺度
                colorbar=dict(title='Win Rate (%)'),
                showscale=True
            ),
            text=aggregated['win_rate'].round(2),  # 悬停显示胜率
            hovertemplate='EMA: %{x}<br>ATR: %{y}<br>Multiplier: %{z}<br>Win Rate: %{text}%'
        )])
        
        fig.update_layout(
            title=title,
            scene=dict(
                xaxis_title='EMA Period',
                yaxis_title='ATR Period',
                zaxis_title='Multiplier'
            )
        )
        
        # 保存为 HTML 文件
        cube_filename = f'{batch_folder}/3d_heatmap_cube.html'
        fig.write_html(cube_filename)
        print(f"3D 热力图魔方已保存到: {cube_filename}")
        return fig
    except Exception as e:
        print(f"函数内部错误: {e}")
        return None

def custom_maximize(stats):
    # 检查交易数量和胜率有效性
    if (stats['# Trades'] < 0 or
        pd.isna(stats['Win Rate [%]'])):
        return 0
    # 直接返回胜率（百分比形式）
    return stats['Win Rate [%]']

# 删除压缩包文件夹
def delete_zip_folder(symbol, interval, save_dir):
    """
    删除指定符号和间隔的压缩包文件夹。
    
    参数:
    - symbol: 交易对符号，如 'BTCUSDT'
    - interval: 时间间隔，如 '1m'
    - save_dir: 保存目录路径，如 'back_test/data'
    """
    zip_folder = f'{save_dir}/{symbol}_{interval}'
    if os.path.exists(zip_folder):
        print(f"删除压缩包文件夹: {zip_folder}")
        shutil.rmtree(zip_folder)


