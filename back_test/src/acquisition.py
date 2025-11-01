import os  # 导入 os 库，用于文件和路径操作

from .utils import load_and_process_data, download_binance_data, unzip_binance_data, merge_csv_files_by_years_months, delete_zip_folder  # 修改为相对导入

def acquire_data(symbol, interval, selected_years=None, selected_months=None, save_dir='back_test/data'):

    if selected_years and selected_months:
        # 检查所需子文件是否存在
        files_exist = True
        for year in selected_years:
            for month in selected_months:
                file_path = f'{save_dir}/{symbol}-{interval}/{symbol}-{interval}-{year}-{month:02d}.csv'
                if not os.path.exists(file_path):
                    files_exist = False
                    break
            if not files_exist:
                break
        
        if not files_exist:
            # 下载并解压数据
            download_binance_data(symbol=symbol, interval=interval, years=selected_years, months=selected_months, save_dir=save_dir)
            unzip_binance_data(symbol=symbol, interval=interval, save_dir=save_dir)
            delete_zip_folder(symbol, interval, save_dir)
        
        # 合并并加载数据
        input_dir = f'{save_dir}/{symbol}-{interval}'
        output_file = f'{save_dir}/merged_{symbol}-{interval}.csv'
        merged_data = merge_csv_files_by_years_months(
            symbol=symbol, interval=interval, years=selected_years, months=selected_months,
            input_dir=input_dir, output_file=output_file
        )
        data = load_and_process_data(output_file)
    else:
        # 加载默认文件
        data = load_and_process_data(f'{save_dir}/{symbol}-{interval}/{symbol}-{interval}-2025-01.csv')
    
    return data