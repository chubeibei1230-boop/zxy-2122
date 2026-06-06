import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os


class MaterialDataProcessor:
    def __init__(self):
        self.data_dir = 'data'
        self.reports_dir = 'reports'
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.reports_dir, exist_ok=True)

    def load_data(self, file_path=None):
        if file_path and os.path.exists(file_path):
            df = pd.read_csv(file_path)
        else:
            default_path = os.path.join('sample_data', 'materials_usage.csv')
            df = pd.read_csv(default_path)
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        df = df.dropna(subset=['日期'])
        df = df.sort_values(['材料名称', '日期'])
        return df

    def save_uploaded_data(self, df, filename='uploaded_materials.csv'):
        save_path = os.path.join(self.data_dir, filename)
        df.to_csv(save_path, index=False, encoding='utf-8-sig')
        return save_path

    def calculate_moving_average(self, df, window=7):
        result = []
        for material in df['材料名称'].unique():
            mat_df = df[df['材料名称'] == material].copy()
            mat_df = mat_df.sort_values('日期')
            mat_df['移动平均'] = mat_df['计划用量'].rolling(window=window, min_periods=1).mean().round(2)
            result.append(mat_df)
        return pd.concat(result, ignore_index=True)

    def simulate_actual_usage(self, df, loss_rate=0.05):
        df = df.copy()
        np.random.seed(42)
        base_variation = np.random.normal(1, 0.03, len(df))
        df['实际用量'] = (df['计划用量'] * base_variation * (1 + loss_rate)).round(2)
        df['损耗量'] = (df['实际用量'] - df['计划用量']).round(2)
        df['损耗率%'] = ((df['损耗量'] / df['计划用量']) * 100).round(2)
        return df

    def calculate_replenishment(self, df, safety_stock=0.2, replenish_interval=7):
        result = []
        for material in df['材料名称'].unique():
            mat_df = df[df['材料名称'] == material].copy()
            mat_df = mat_df.sort_values('日期')
            mat_df['累计用量'] = mat_df['实际用量'].cumsum()
            avg_daily = mat_df['实际用量'].mean()
            safety_level = avg_daily * safety_stock * replenish_interval
            mat_df['安全库存水平'] = safety_level
            mat_df['建议补货量'] = 0.0
            for i in range(len(mat_df)):
                if i % replenish_interval == 0 and i > 0:
                    period_usage = mat_df['实际用量'].iloc[i - replenish_interval:i].sum()
                    current_stock = safety_level - (period_usage - avg_daily * replenish_interval * 0.1)
                    replenish_amount = max(0, (safety_level * 1.5 - current_stock))
                    mat_df.iloc[i, mat_df.columns.get_loc('建议补货量')] = round(replenish_amount, 2)
            mat_df['库存预警'] = mat_df['建议补货量'] > 0
            result.append(mat_df)
        return pd.concat(result, ignore_index=True)

    def run_simulation(self, df, loss_rate=0.05, ma_window=7, safety_stock=0.2, replenish_interval=7):
        df = self.calculate_moving_average(df, window=ma_window)
        df = self.simulate_actual_usage(df, loss_rate=loss_rate)
        df = self.calculate_replenishment(df, safety_stock=safety_stock, replenish_interval=replenish_interval)
        return df

    def get_material_summary(self, df):
        summary = df.groupby(['材料名称', '规格', '单位']).agg({
            '计划用量': ['sum', 'mean'],
            '实际用量': ['sum', 'mean'],
            '损耗量': 'sum',
            '损耗率%': 'mean',
            '移动平均': 'last',
            '建议补货量': 'sum'
        }).round(2)
        summary.columns = ['计划总量', '日均计划', '实际总量', '日均实际', '总损耗', '平均损耗率%', '期末移动平均', '建议补货总量']
        summary = summary.reset_index()
        summary['总计划成本'] = (summary['计划总量'] * df.groupby('材料名称')['单价'].first().values).round(2)
        summary['总实际成本'] = (summary['实际总量'] * df.groupby('材料名称')['单价'].first().values).round(2)
        summary['成本差异'] = (summary['总实际成本'] - summary['总计划成本']).round(2)
        return summary

    def export_report(self, df, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'材料用量分析报告_{timestamp}.xlsx'
        filepath = os.path.join(self.reports_dir, filename)
        summary = self.get_material_summary(df)
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='明细数据', index=False)
            summary.to_excel(writer, sheet_name='汇总分析', index=False)
        return filepath

    def export_csv(self, df, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'材料用量数据_{timestamp}.csv'
        filepath = os.path.join(self.reports_dir, filename)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath
