import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import json
import uuid


class MaterialDataProcessor:
    def __init__(self):
        self.data_dir = 'data'
        self.reports_dir = 'reports'
        self.alerts_file = os.path.join(self.data_dir, 'alerts.json')
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

    def detect_high_loss_alerts(self, df, consecutive_days=2, loss_threshold_pct=6):
        alerts = []
        for material in df['材料名称'].unique():
            mat_df = df[df['材料名称'] == material].sort_values('日期').copy()
            mat_df['连续高损耗'] = (mat_df['损耗率%'] > loss_threshold_pct).rolling(window=consecutive_days, min_periods=consecutive_days).sum()
            high_loss_periods = mat_df[mat_df['连续高损耗'] >= consecutive_days]
            
            for idx, row in high_loss_periods.iterrows():
                end_date = row['日期']
                start_date = mat_df.loc[idx - consecutive_days + 1, '日期'] if idx >= consecutive_days - 1 else row['日期']
                
                avg_loss = mat_df.loc[idx - consecutive_days + 1:idx, '损耗率%'].mean()
                unit_price = row['单价']
                actual_usage = mat_df.loc[idx - consecutive_days + 1:idx, '实际用量'].sum()
                planned_usage = mat_df.loc[idx - consecutive_days + 1:idx, '计划用量'].sum()
                extra_cost = (actual_usage - planned_usage) * unit_price
                
                alert = {
                    'id': str(uuid.uuid4()),
                    'type': '连续损耗偏高',
                    'material': material,
                    'spec': row['规格'],
                    'unit': row['单位'],
                    'start_date': str(start_date.date()),
                    'end_date': str(end_date.date()),
                    'level': self._determine_alert_level(avg_loss, loss_threshold_pct),
                    'description': f'连续{consecutive_days}天损耗率超过{loss_threshold_pct}%，平均损耗率{avg_loss:.2f}%',
                    'avg_loss_pct': round(avg_loss, 2),
                    'extra_cost': round(extra_cost, 2),
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'status': '待处理',
                    'clerk_note': '',
                    'supervisor_comment': '',
                    'handled_by': '',
                    'handled_at': ''
                }
                alerts.append(alert)
        return alerts

    def detect_cost_deviation_alerts(self, df, cost_deviation_pct=3):
        alerts = []
        summary = self.get_material_summary(df)
        
        for _, row in summary.iterrows():
            if row['总计划成本'] > 0:
                deviation_pct = (row['成本差异'] / row['总计划成本']) * 100
                if abs(deviation_pct) > cost_deviation_pct and row['成本差异'] > 0:
                    alert = {
                        'id': str(uuid.uuid4()),
                        'type': '成本偏离过大',
                        'material': row['材料名称'],
                        'spec': row['规格'],
                        'unit': row['单位'],
                        'start_date': str(df['日期'].min().date()),
                        'end_date': str(df['日期'].max().date()),
                        'level': self._determine_cost_level(deviation_pct),
                        'description': f'实际成本较计划成本偏离{deviation_pct:.2f}%，超出阈值{cost_deviation_pct}%',
                        'avg_loss_pct': round(row['平均损耗率%'], 2),
                        'extra_cost': round(row['成本差异'], 2),
                        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': '待处理',
                        'clerk_note': '',
                        'supervisor_comment': '',
                        'handled_by': '',
                        'handled_at': ''
                    }
                    alerts.append(alert)
        return alerts

    def detect_replenish_volatility_alerts(self, df, volatility_threshold=1.0):
        alerts = []
        for material in df['材料名称'].unique():
            mat_df = df[df['材料名称'] == material].sort_values('日期').copy()
            replenish_values = mat_df[mat_df['建议补货量'] > 0]['建议补货量']
            
            if len(replenish_values) >= 2:
                mean_replenish = replenish_values.mean()
                std_replenish = replenish_values.std()
                
                if std_replenish > 0:
                    for idx, row in mat_df.iterrows():
                        if row['建议补货量'] > 0:
                            z_score = abs(row['建议补货量'] - mean_replenish) / std_replenish if std_replenish > 0 else 0
                            if z_score > volatility_threshold:
                                alert = {
                                    'id': str(uuid.uuid4()),
                                    'type': '补货异常波动',
                                    'material': material,
                                    'spec': row['规格'],
                                    'unit': row['单位'],
                                    'start_date': str(row['日期'].date()),
                                    'end_date': str(row['日期'].date()),
                                    'level': '中' if z_score < 3 else '高',
                                    'description': f'建议补货量{row["建议补货量"]}异常波动，偏离均值{z_score:.1f}个标准差',
                                    'avg_loss_pct': round(row['损耗率%'], 2),
                                    'extra_cost': round(row['建议补货量'] * row['单价'] * 0.2, 2),
                                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'status': '待处理',
                                    'clerk_note': '',
                                    'supervisor_comment': '',
                                    'handled_by': '',
                                    'handled_at': ''
                                }
                                alerts.append(alert)
        return alerts

    def _determine_alert_level(self, avg_loss, threshold):
        ratio = avg_loss / threshold
        if ratio >= 2:
            return '高'
        elif ratio >= 1.5:
            return '中'
        else:
            return '低'

    def _determine_cost_level(self, deviation_pct):
        if deviation_pct >= 30:
            return '高'
        elif deviation_pct >= 20:
            return '中'
        else:
            return '低'

    def generate_all_alerts(self, df):
        loss_alerts = self.detect_high_loss_alerts(df)
        cost_alerts = self.detect_cost_deviation_alerts(df)
        replenish_alerts = self.detect_replenish_volatility_alerts(df)
        
        all_alerts = loss_alerts + cost_alerts + replenish_alerts
        
        existing_alerts = self.load_alerts()
        existing_keys = {(a['material'], a['type'], a['start_date'], a['end_date']) for a in existing_alerts}
        
        new_alerts = []
        for alert in all_alerts:
            key = (alert['material'], alert['type'], alert['start_date'], alert['end_date'])
            if key not in existing_keys:
                new_alerts.append(alert)
        
        if new_alerts:
            self.save_alerts(existing_alerts + new_alerts)
        
        return existing_alerts + new_alerts

    def load_alerts(self):
        if os.path.exists(self.alerts_file):
            try:
                with open(self.alerts_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save_alerts(self, alerts):
        with open(self.alerts_file, 'w', encoding='utf-8') as f:
            json.dump(alerts, f, ensure_ascii=False, indent=2)

    def update_alert_clerk_note(self, alert_id, note):
        alerts = self.load_alerts()
        for alert in alerts:
            if alert['id'] == alert_id:
                alert['clerk_note'] = note
                if alert['status'] == '待处理':
                    alert['status'] = '已确认'
        self.save_alerts(alerts)
        return alerts

    def update_alert_supervisor(self, alert_id, status, comment, handled_by='项目主管'):
        alerts = self.load_alerts()
        for alert in alerts:
            if alert['id'] == alert_id:
                alert['status'] = status
                alert['supervisor_comment'] = comment
                alert['handled_by'] = handled_by
                alert['handled_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.save_alerts(alerts)
        return alerts

    def get_alert_summary(self, alerts):
        if not alerts:
            return {
                'total': 0,
                'pending': 0,
                'confirmed': 0,
                'resolved': 0,
                'high': 0,
                'medium': 0,
                'low': 0,
                'total_extra_cost': 0
            }
        
        df = pd.DataFrame(alerts)
        return {
            'total': len(df),
            'pending': len(df[df['status'] == '待处理']),
            'confirmed': len(df[df['status'] == '已确认']),
            'resolved': len(df[df['status'] == '已处理']),
            'high': len(df[df['level'] == '高']),
            'medium': len(df[df['level'] == '中']),
            'low': len(df[df['level'] == '低']),
            'total_extra_cost': round(df['extra_cost'].sum(), 2)
        }

    def get_top_risk_materials(self, alerts, top_n=5):
        if not alerts:
            return pd.DataFrame()
        
        df = pd.DataFrame(alerts)
        material_risk = df.groupby('material').agg({
            'extra_cost': 'sum',
            'id': 'count',
            'level': lambda x: (x == '高').sum()
        }).rename(columns={'id': 'alert_count', 'level': 'high_count'})
        
        material_risk = material_risk.sort_values(['high_count', 'extra_cost'], ascending=False).head(top_n)
        return material_risk.reset_index()

    def export_report_with_alerts(self, df, alerts, filename=None):
        if filename is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'材料用量分析报告_含预警_{timestamp}.xlsx'
        filepath = os.path.join(self.reports_dir, filename)
        
        summary = self.get_material_summary(df)
        alert_summary = self.get_alert_summary(alerts)
        top_risks = self.get_top_risk_materials(alerts)
        
        alert_df = pd.DataFrame(alerts) if alerts else pd.DataFrame()
        overview_df = pd.DataFrame([alert_summary])
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='明细数据', index=False)
            summary.to_excel(writer, sheet_name='汇总分析', index=False)
            
            if not alert_df.empty:
                alert_df.to_excel(writer, sheet_name='预警明细', index=False)
            
            overview_df.to_excel(writer, sheet_name='异常概览', index=False)
            
            if not top_risks.empty:
                top_risks.to_excel(writer, sheet_name='重点材料风险', index=False)
        
        return filepath
