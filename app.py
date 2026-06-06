import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objs as go
import pandas as pd
import numpy as np
import base64
import io
from data_processor import MaterialDataProcessor

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server
processor = MaterialDataProcessor()

REQUIRED_COLUMNS = ['日期', '材料名称', '规格', '计划用量', '单位', '单价']

default_df = processor.load_data()
default_simulated = processor.run_simulation(default_df)

app.layout = html.Div([
    dcc.Store(id='stored-data', data=default_simulated.to_dict('records')),
    dcc.Store(id='original-data', data=default_df.to_dict('records')),
    dcc.Store(id='baseline-data', data=default_simulated.to_dict('records')),
    dcc.Store(id='current-simulated-data', data=default_simulated.to_dict('records')),
    dcc.Store(id='alerts-data', data=[]),
    dcc.Store(id='selected-alert-id', data=''),
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(
        children=[
            dbc.NavItem(dbc.NavLink("资料员", href="/clerk", id="nav-clerk")),
            dbc.NavItem(dbc.NavLink("项目主管", href="/supervisor", id="nav-supervisor")),
            dbc.NavItem(dbc.NavLink("成本人员", href="/cost", id="nav-cost")),
            dbc.NavItem(dbc.NavLink("预警管理", href="/alerts", id="nav-alerts")),
        ],
        brand="施工项目材料用量可视化系统",
        brand_href="/",
        color="primary",
        dark=True,
        className="mb-4"
    ),
    dbc.Container(id='page-content', fluid=True)
])


def serve_home():
    return dbc.Row([
        dbc.Col(
            dbc.Card([
                dbc.CardHeader("系统概览"),
                dbc.CardBody([
                    html.H4("欢迎使用施工项目材料用量可视化系统", className="card-title"),
                    html.P("请选择您的角色进入相应功能模块：", className="card-text"),
                    dbc.Row([
                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.H5("资料员", className="card-title"),
                                html.P("上传材料用量表，管理基础数据", className="card-text"),
                                dbc.Button("进入", color="primary", href="/clerk")
                            ])
                        ], className="mb-3")),
                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.H5("项目主管", className="card-title"),
                                html.P("调整模拟参数，对比分析趋势", className="card-text"),
                                dbc.Button("进入", color="primary", href="/supervisor")
                            ])
                        ], className="mb-3")),
                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.H5("成本人员", className="card-title"),
                                html.P("导出分析报告，管控材料成本", className="card-text"),
                                dbc.Button("进入", color="primary", href="/cost")
                            ])
                        ], className="mb-3")),
                        dbc.Col(dbc.Card([
                            dbc.CardBody([
                                html.H5("预警管理", className="card-title"),
                                html.P("材料异常预警与处置跟踪", className="card-text"),
                                dbc.Button("进入", color="danger", href="/alerts")
                            ])
                        ], className="mb-3"))
                    ])
                ])
            ]),
            width=12
        )
    ])


def serve_clerk():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H4("资料员工作台 - 数据上传"),
                html.Hr(),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        '拖拽CSV文件到此处 或 ',
                        html.A('点击选择文件')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px 0'
                    },
                    multiple=False
                ),
                html.Div(id='upload-status', className='mt-2'),
                dbc.Button('加载示例数据', id='load-sample-btn', color='secondary', className='mt-2 mb-4'),
                html.Div([
                    html.H6("必填字段说明："),
                    html.Small("日期, 材料名称, 规格, 计划用量, 单位, 单价", className="text-muted")
                ])
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                html.H5("数据预览"),
                html.Div(id='data-preview-table')
            ], width=12)
        ])
    ])


def serve_supervisor():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H4("项目主管工作台 - 参数模拟"),
                html.Hr()
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("模拟参数设置"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("损耗率 (%)"),
                                dcc.Slider(id='loss-rate-slider', min=0, max=20, step=0.5, value=5,
                                           marks={i: f'{i}%' for i in range(0, 21, 5)}),
                                html.Div(id='loss-rate-value', className='text-center mt-1')
                            ], md=6),
                            dbc.Col([
                                html.Label("安全库存系数"),
                                dcc.Slider(id='safety-stock-slider', min=0.1, max=0.5, step=0.05, value=0.2,
                                           marks={0.1: '10%', 0.2: '20%', 0.3: '30%', 0.4: '40%', 0.5: '50%'}),
                                html.Div(id='safety-stock-value', className='text-center mt-1')
                            ], md=6),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                html.Label("补货间隔 (天)"),
                                dcc.Slider(id='replenish-slider', min=3, max=30, step=1, value=7,
                                           marks={i: f'{i}天' for i in [3, 7, 14, 21, 30]}),
                                html.Div(id='replenish-value', className='text-center mt-1')
                            ], md=6),
                            dbc.Col([
                                html.Label("移动平均窗口 (天)"),
                                dcc.Slider(id='ma-slider', min=3, max=14, step=1, value=7,
                                           marks={i: f'{i}天' for i in [3, 5, 7, 10, 14]}),
                                html.Div(id='ma-value', className='text-center mt-1')
                            ], md=6),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                html.Label("选择材料"),
                                dcc.Dropdown(id='material-dropdown', multi=False)
                            ], md=12),
                        ], className='mt-3'),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button('设为基准', id='set-baseline-btn', color='secondary', className='mt-3 me-2'),
                                dbc.Button('运行模拟', id='run-simulation-btn', color='primary', className='mt-3'),
                            ]),
                        ]),
                        html.Div(id='baseline-info', className='mt-2 text-muted small')
                    ])
                ])
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("用量趋势对比（基准 vs 当前）"),
                    dbc.CardBody([
                        dcc.Graph(id='trend-chart')
                    ])
                ])
            ], width=12)
        ], className='mt-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("损耗率趋势对比"),
                    dbc.CardBody([
                        dcc.Graph(id='loss-chart')
                    ])
                ])
            ], md=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("补货建议"),
                    dbc.CardBody([
                        dcc.Graph(id='replenish-chart')
                    ])
                ])
            ], md=6),
        ], className='mt-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("模拟结果对比汇总"),
                    dbc.CardBody([
                        html.Div(id='simulation-summary')
                    ])
                ])
            ], width=12)
        ], className='mt-4')
    ])


def serve_cost():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H4("成本人员工作台 - 报告导出"),
                html.Hr(),
                html.Div(id='cost-sync-info', className='text-info small mb-2')
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("材料成本汇总"),
                    dbc.CardBody([
                        html.Div(id='cost-summary-table')
                    ])
                ])
            ], width=12)
        ], className='mb-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("成本分析图表"),
                    dbc.CardBody([
                        dcc.Graph(id='cost-chart')
                    ])
                ])
            ], width=12)
        ], className='mb-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("预警成本影响汇总"),
                    dbc.CardBody([
                        html.Div(id='cost-alert-summary')
                    ])
                ])
            ], width=12)
        ], className='mb-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("重点材料风险排行"),
                    dbc.CardBody([
                        dcc.Graph(id='risk-chart')
                    ])
                ])
            ], width=12)
        ], className='mb-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("导出报告"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                dbc.Button('导出Excel报告(含预警)', id='export-excel-btn', color='success', className='me-2'),
                                dbc.Button('导出CSV数据', id='export-csv-btn', color='info', className='me-2'),
                            ]),
                        ]),
                        html.Div(id='export-status', className='mt-3'),
                        dcc.Download(id='download-excel'),
                        dcc.Download(id='download-csv'),
                    ])
                ])
            ], width=12)
        ])
    ])


def get_level_badge(level):
    color_map = {'高': 'danger', '中': 'warning', '低': 'info'}
    return dbc.Badge(level, color=color_map.get(level, 'secondary'))


def get_status_badge(status):
    color_map = {'待处理': 'secondary', '已确认': 'primary', '已处理': 'success'}
    return dbc.Badge(status, color=color_map.get(status, 'light'))


def serve_alerts():
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H4("材料异常预警与处置跟踪"),
                html.Hr()
            ], width=12)
        ]),
        dbc.Row([
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("预警总数", className="card-title"),
                html.H3(id='alert-total', className="text-primary")
            ])), md=2),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("待处理", className="card-title"),
                html.H3(id='alert-pending', className="text-danger")
            ])), md=2),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("已确认", className="card-title"),
                html.H3(id='alert-confirmed', className="text-warning")
            ])), md=2),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("已处理", className="card-title"),
                html.H3(id='alert-resolved', className="text-success")
            ])), md=2),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("高等级预警", className="card-title"),
                html.H3(id='alert-high', className="text-danger")
            ])), md=2),
            dbc.Col(dbc.Card(dbc.CardBody([
                html.H5("涉及额外成本", className="card-title"),
                html.H3(id='alert-cost', className="text-warning")
            ])), md=2),
        ], className='mb-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("筛选条件"),
                    dbc.CardBody([
                        dbc.Row([
                            dbc.Col([
                                html.Label("材料名称"),
                                dcc.Dropdown(id='alert-material-filter', multi=True, placeholder="选择材料")
                            ], md=3),
                            dbc.Col([
                                html.Label("预警等级"),
                                dcc.Dropdown(id='alert-level-filter', multi=True,
                                             options=[{'label': '高', 'value': '高'},
                                                      {'label': '中', 'value': '中'},
                                                      {'label': '低', 'value': '低'}],
                                             placeholder="选择等级")
                            ], md=3),
                            dbc.Col([
                                html.Label("处理状态"),
                                dcc.Dropdown(id='alert-status-filter', multi=True,
                                             options=[{'label': '待处理', 'value': '待处理'},
                                                      {'label': '已确认', 'value': '已确认'},
                                                      {'label': '已处理', 'value': '已处理'}],
                                             placeholder="选择状态")
                            ], md=3),
                            dbc.Col([
                                html.Label("日期范围"),
                                dcc.DatePickerRange(id='alert-date-range', display_format='YYYY-MM-DD')
                            ], md=3),
                        ]),
                        dbc.Row([
                            dbc.Col([
                                dbc.Button('重置筛选', id='reset-alert-filter', color='secondary', className='mt-3 me-2'),
                                dbc.Button('刷新预警', id='refresh-alerts-btn', color='primary', className='mt-3'),
                            ])
                        ])
                    ])
                ])
            ], width=12)
        ], className='mb-4'),
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("预警列表"),
                    dbc.CardBody([
                        html.Div(id='alerts-table-container')
                    ])
                ])
            ], width=12)
        ]),
        dbc.Modal([
            dbc.ModalHeader(id='alert-modal-title'),
            dbc.ModalBody([
                html.Div(id='alert-modal-content')
            ]),
            dbc.ModalFooter([
                dbc.Button("关闭", id="close-alert-modal", color="secondary")
            ]),
        ], id="alert-modal", size="lg"),
    ])


@app.callback(Output('page-content', 'children'),
              [Input('url', 'pathname')])
def display_page(pathname):
    if pathname == '/clerk':
        return serve_clerk()
    elif pathname == '/supervisor':
        return serve_supervisor()
    elif pathname == '/cost':
        return serve_cost()
    elif pathname == '/alerts':
        return serve_alerts()
    else:
        return serve_home()


@app.callback(
    [Output('loss-rate-value', 'children'),
     Output('safety-stock-value', 'children'),
     Output('replenish-value', 'children'),
     Output('ma-value', 'children')],
    [Input('loss-rate-slider', 'value'),
     Input('safety-stock-slider', 'value'),
     Input('replenish-slider', 'value'),
     Input('ma-slider', 'value')]
)
def update_slider_values(loss_rate, safety_stock, replenish, ma):
    return (
        f"当前: {loss_rate}%",
        f"当前: {safety_stock * 100:.0f}%",
        f"当前: {replenish}天",
        f"当前: {ma}天"
    )


def validate_dataframe(df):
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing_cols:
        return False, f"缺少必填字段: {', '.join(missing_cols)}。请确保包含字段: {', '.join(REQUIRED_COLUMNS)}"
    
    if len(df) == 0:
        return False, "上传的数据为空，请检查文件内容"
    
    if '材料名称' not in df.columns or df['材料名称'].nunique() == 0:
        return False, "未找到任何材料数据，请检查'材料名称'列"
    
    return True, None


def parse_contents(contents, filename):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename.lower():
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        elif 'xls' in filename.lower():
            df = pd.read_excel(io.BytesIO(decoded))
        else:
            return None, "不支持的文件格式，请上传CSV或Excel文件"
        return df, None
    except Exception as e:
        return None, f"文件解析错误: {str(e)}"


@app.callback(
    [Output('stored-data', 'data'),
     Output('original-data', 'data'),
     Output('upload-status', 'children')],
    [Input('upload-data', 'contents'),
     Input('load-sample-btn', 'n_clicks')],
    [State('upload-data', 'filename')]
)
def update_data(contents, n_clicks, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        default_df = processor.load_data()
        simulated = processor.run_simulation(default_df)
        return simulated.to_dict('records'), default_df.to_dict('records'), ""
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'load-sample-btn':
        default_df = processor.load_data()
        simulated = processor.run_simulation(default_df)
        return simulated.to_dict('records'), default_df.to_dict('records'), dbc.Alert("已加载示例数据", color="success")
    
    if trigger_id == 'upload-data' and contents is not None:
        df, error = parse_contents(contents, filename)
        if error:
            default_df = processor.load_data()
            simulated = processor.run_simulation(default_df)
            return simulated.to_dict('records'), default_df.to_dict('records'), dbc.Alert(error, color="danger")
        
        valid, validation_error = validate_dataframe(df)
        if not valid:
            default_df = processor.load_data()
            simulated = processor.run_simulation(default_df)
            return simulated.to_dict('records'), default_df.to_dict('records'), dbc.Alert(validation_error, color="danger")
        
        try:
            processor.save_uploaded_data(df)
            simulated = processor.run_simulation(df)
            return simulated.to_dict('records'), df.to_dict('records'), dbc.Alert(f"成功上传文件: {filename}，共 {len(df)} 条数据，{df['材料名称'].nunique()} 种材料", color="success")
        except Exception as e:
            default_df = processor.load_data()
            simulated = processor.run_simulation(default_df)
            return simulated.to_dict('records'), default_df.to_dict('records'), dbc.Alert(f"数据处理失败: {str(e)}", color="danger")
    
    default_df = processor.load_data()
    simulated = processor.run_simulation(default_df)
    return simulated.to_dict('records'), default_df.to_dict('records'), ""


@app.callback(
    Output('baseline-data', 'data'),
    [Input('stored-data', 'data'),
     Input('set-baseline-btn', 'n_clicks')],
    [State('current-simulated-data', 'data')]
)
def update_baseline(stored_data, set_baseline_clicks, current_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return stored_data
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'stored-data':
        return stored_data
    
    if trigger_id == 'set-baseline-btn' and set_baseline_clicks is not None:
        if current_data:
            return current_data
    
    return dash.no_update


@app.callback(
    Output('current-simulated-data', 'data'),
    [Input('stored-data', 'data'),
     Input('run-simulation-btn', 'n_clicks')],
    [State('loss-rate-slider', 'value'),
     State('safety-stock-slider', 'value'),
     State('replenish-slider', 'value'),
     State('ma-slider', 'value'),
     State('original-data', 'data')]
)
def update_current_simulated(stored_data, run_clicks, loss_rate, safety_stock, replenish_interval, ma_window, original_data):
    ctx = dash.callback_context
    if not ctx.triggered:
        return stored_data
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'stored-data':
        return stored_data
    
    if trigger_id == 'run-simulation-btn' and run_clicks is not None:
        if not original_data:
            return dash.no_update
        
        df = pd.DataFrame(original_data)
        loss_rate_decimal = loss_rate / 100.0
        
        simulated = processor.run_simulation(
            df,
            loss_rate=loss_rate_decimal,
            ma_window=ma_window,
            safety_stock=safety_stock,
            replenish_interval=replenish_interval
        )
        
        return simulated.to_dict('records')
    
    return dash.no_update


@app.callback(
    Output('data-preview-table', 'children'),
    [Input('original-data', 'data')]
)
def update_preview(data):
    if not data:
        return html.Div("暂无数据")
    df = pd.DataFrame(data)
    return dash_table.DataTable(
        data=df.head(20).to_dict('records'),
        columns=[{'name': i, 'id': i} for i in df.columns],
        page_size=10,
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '10px'}
    )


@app.callback(
    [Output('material-dropdown', 'options'),
     Output('material-dropdown', 'value')],
    [Input('current-simulated-data', 'data')]
)
def update_material_dropdown(data):
    if not data:
        return [], None
    df = pd.DataFrame(data)
    if '材料名称' not in df.columns:
        return [], None
    materials = df['材料名称'].unique()
    if len(materials) == 0:
        return [], None
    options = [{'label': m, 'value': m} for m in materials]
    return options, materials[0]


@app.callback(
    Output('baseline-info', 'children'),
    [Input('baseline-data', 'data')]
)
def update_baseline_info(data):
    if not data:
        return ""
    df = pd.DataFrame(data)
    return f"当前基准数据: {len(df)} 条记录，损耗率约 {df['损耗率%'].mean():.2f}%"


@app.callback(
    [Output('trend-chart', 'figure'),
     Output('loss-chart', 'figure'),
     Output('replenish-chart', 'figure'),
     Output('simulation-summary', 'children')],
    [Input('current-simulated-data', 'data'),
     Input('material-dropdown', 'value'),
     Input('baseline-data', 'data')],
    [State('loss-rate-slider', 'value'),
     State('ma-slider', 'value')]
)
def update_charts(current_data, material, baseline_data, loss_rate, ma_window):
    if not current_data or not material or not baseline_data:
        return {}, {}, {}, html.Div("请选择材料")
    
    simulated = pd.DataFrame(current_data)
    baseline_df = pd.DataFrame(baseline_data)
    
    mat_data = simulated[simulated['材料名称'] == material].sort_values('日期')
    baseline_mat = baseline_df[baseline_df['材料名称'] == material].sort_values('日期')
    
    if len(mat_data) == 0:
        return {}, {}, {}, html.Div("未找到该材料的数据")
    
    trend_fig = go.Figure()
    
    if len(baseline_mat) > 0:
        trend_fig.add_trace(go.Scatter(x=baseline_mat['日期'], y=baseline_mat['实际用量'], mode='lines', name='基准-实际用量', line=dict(color='#9467bd', width=2, dash='dot'), opacity=0.7))
    
    trend_fig.add_trace(go.Scatter(x=mat_data['日期'], y=mat_data['计划用量'], mode='lines+markers', name='计划用量', line=dict(color='#1f77b4', width=2)))
    trend_fig.add_trace(go.Scatter(x=mat_data['日期'], y=mat_data['实际用量'], mode='lines+markers', name='当前-实际用量', line=dict(color='#ff7f0e', width=2)))
    trend_fig.add_trace(go.Scatter(x=mat_data['日期'], y=mat_data['移动平均'], mode='lines', name=f'{ma_window}天移动平均', line=dict(color='#2ca02c', width=3, dash='dash')))
    trend_fig.update_layout(title=f'{material} - 用量趋势对比分析', xaxis_title='日期', yaxis_title='用量', legend=dict(orientation='h', y=-0.2), height=450, hovermode='x unified')
    
    loss_fig = go.Figure()
    
    if len(baseline_mat) > 0:
        loss_fig.add_trace(go.Bar(x=baseline_mat['日期'], y=baseline_mat['损耗率%'], name='基准-损耗率%', marker_color='#9467bd', opacity=0.5))
    
    loss_fig.add_trace(go.Bar(x=mat_data['日期'], y=mat_data['损耗率%'], name='当前-损耗率%', marker_color='#d62728'))
    loss_fig.add_hline(y=loss_rate, line_dash="dash", line_color="red", annotation_text=f"目标损耗率: {loss_rate}%")
    loss_fig.update_layout(title=f'{material} - 损耗率趋势对比', xaxis_title='日期', yaxis_title='损耗率 (%)', height=350, barmode='group')
    
    replenish_fig = go.Figure()
    replenish_fig.add_trace(go.Scatter(x=mat_data['日期'], y=mat_data['累计用量'], mode='lines', name='累计用量', fill='tozeroy', line=dict(color='#9467bd')))
    replenish_points = mat_data[mat_data['建议补货量'] > 0]
    if len(replenish_points) > 0:
        replenish_fig.add_trace(go.Scatter(x=replenish_points['日期'], y=replenish_points['累计用量'], mode='markers', marker=dict(size=12, symbol='triangle-up', color='red'), name='补货点', text=replenish_points['建议补货量'], hovertemplate='日期: %{x}<br>建议补货量: %{text}'))
    replenish_fig.update_layout(title=f'{material} - 累计用量与补货建议', xaxis_title='日期', yaxis_title='累计用量', height=350)
    
    summary = processor.get_material_summary(simulated)
    baseline_summary = processor.get_material_summary(baseline_df)
    
    mat_summary = summary[summary['材料名称'] == material].iloc[0]
    
    if len(baseline_summary[baseline_summary['材料名称'] == material]) > 0:
        baseline_mat_summary = baseline_summary[baseline_summary['材料名称'] == material].iloc[0]
        
        cost_diff = mat_summary['总实际成本'] - baseline_mat_summary['总实际成本']
        cost_diff_text = f"{'+' if cost_diff > 0 else ''}{cost_diff:,.0f}"
        cost_diff_color = "text-danger" if cost_diff > 0 else "text-success"
        
        loss_diff = mat_summary['平均损耗率%'] - baseline_mat_summary['平均损耗率%']
        loss_diff_text = f"{'+' if loss_diff > 0 else ''}{loss_diff:.2f}%"
        
        baseline_actual = baseline_mat_summary['实际总量']
        baseline_loss = baseline_mat_summary['总损耗']
        baseline_cost = baseline_mat_summary['总实际成本']
    else:
        cost_diff_text = "N/A"
        cost_diff_color = "text-muted"
        loss_diff_text = "N/A"
        baseline_actual = "N/A"
        baseline_loss = "N/A"
        baseline_cost = "N/A"
    
    summary_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("计划总量", className="card-title"),
            html.H3(f"{mat_summary['计划总量']} {mat_summary['单位']}", className="text-primary")
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("实际总量", className="card-title"),
            html.H3(f"{mat_summary['实际总量']} {mat_summary['单位']}", className="text-warning"),
            html.Small(f"基准: {baseline_actual}", className="text-muted")
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("总损耗", className="card-title"),
            html.H3(f"{mat_summary['总损耗']} {mat_summary['单位']}", className="text-danger"),
            html.Small(f"基准: {baseline_loss}", className="text-muted")
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("平均损耗率", className="card-title"),
            html.H3(f"{mat_summary['平均损耗率%']}%", className="text-info"),
            html.Small(f"{loss_diff_text} 较基准", className=cost_diff_color)
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("总实际成本", className="card-title"),
            html.H3(f"¥{mat_summary['总实际成本']:,.0f}", className="text-warning"),
            html.Small(f"基准: ¥{baseline_cost:,.0f}" if isinstance(baseline_cost, (int, float)) else f"基准: {baseline_cost}", className="text-muted")
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("成本差异(较基准)", className="card-title"),
            html.H3(f"¥{cost_diff_text}", className=cost_diff_color)
        ])), md=2),
    ])
    
    return trend_fig, loss_fig, replenish_fig, summary_cards


@app.callback(
    [Output('cost-summary-table', 'children'),
     Output('cost-chart', 'figure'),
     Output('cost-sync-info', 'children')],
    [Input('current-simulated-data', 'data')]
)
def update_cost_page(data):
    if not data:
        return html.Div("暂无数据"), {}, ""
    
    df = pd.DataFrame(data)
    summary = processor.get_material_summary(df)
    
    info_text = f"当前数据包含 {len(df)} 条记录，{df['材料名称'].nunique()} 种材料 - 已同步项目主管的模拟参数"
    
    table = dash_table.DataTable(
        data=summary.to_dict('records'),
        columns=[
            {'name': '材料名称', 'id': '材料名称'},
            {'name': '规格', 'id': '规格'},
            {'name': '单位', 'id': '单位'},
            {'name': '计划总量', 'id': '计划总量'},
            {'name': '实际总量', 'id': '实际总量'},
            {'name': '总损耗', 'id': '总损耗'},
            {'name': '平均损耗率%', 'id': '平均损耗率%'},
            {'name': '总计划成本', 'id': '总计划成本', 'type': 'numeric', 'format': {'specifier': ',.0f'}},
            {'name': '总实际成本', 'id': '总实际成本', 'type': 'numeric', 'format': {'specifier': ',.0f'}},
            {'name': '成本差异', 'id': '成本差异', 'type': 'numeric', 'format': {'specifier': ',.0f'}},
        ],
        style_table={'overflowX': 'auto'},
        style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
        style_cell={'textAlign': 'left', 'padding': '10px'},
        style_data_conditional=[
            {'if': {'column_id': '成本差异', 'filter_query': '{成本差异} > 0'}, 'backgroundColor': '#ffebee', 'color': '#c62828'},
            {'if': {'column_id': '成本差异', 'filter_query': '{成本差异} <= 0'}, 'backgroundColor': '#e8f5e9', 'color': '#2e7d32'},
        ]
    )
    
    cost_fig = go.Figure()
    cost_fig.add_trace(go.Bar(x=summary['材料名称'], y=summary['总计划成本'], name='计划成本', marker_color='#1f77b4'))
    cost_fig.add_trace(go.Bar(x=summary['材料名称'], y=summary['总实际成本'], name='实际成本', marker_color='#ff7f0e'))
    cost_fig.update_layout(title='材料成本对比分析', barmode='group', xaxis_title='材料名称', yaxis_title='金额 (¥)', height=400, legend=dict(orientation='h', y=-0.2))
    
    return table, cost_fig, info_text


@app.callback(
    Output('download-excel', 'data'),
    [Input('export-excel-btn', 'n_clicks')],
    [State('current-simulated-data', 'data'),
     State('alerts-data', 'data')],
    prevent_initial_call=True
)
def export_excel_report(n_clicks, data, alerts):
    if not data:
        return None
    df = pd.DataFrame(data)
    filepath = processor.export_report_with_alerts(df, alerts if alerts else [])
    return dcc.send_file(filepath)


@app.callback(
    Output('download-csv', 'data'),
    [Input('export-csv-btn', 'n_clicks')],
    [State('current-simulated-data', 'data')],
    prevent_initial_call=True
)
def export_csv(n_clicks, data):
    if not data:
        return None
    df = pd.DataFrame(data)
    filepath = processor.export_csv(df)
    return dcc.send_file(filepath)


@app.callback(
    Output('alerts-data', 'data'),
    [Input('current-simulated-data', 'data'),
     Input('refresh-alerts-btn', 'n_clicks')]
)
def update_alerts_data(simulated_data, refresh_clicks):
    if simulated_data:
        df = pd.DataFrame(simulated_data)
        df['日期'] = pd.to_datetime(df['日期'])
        alerts = processor.generate_all_alerts(df)
        return alerts
    return processor.load_alerts()


@app.callback(
    [Output('alert-total', 'children'),
     Output('alert-pending', 'children'),
     Output('alert-confirmed', 'children'),
     Output('alert-resolved', 'children'),
     Output('alert-high', 'children'),
     Output('alert-cost', 'children')],
    [Input('alerts-data', 'data')]
)
def update_alert_cards(alerts):
    summary = processor.get_alert_summary(alerts)
    return (
        summary['total'],
        summary['pending'],
        summary['confirmed'],
        summary['resolved'],
        summary['high'],
        f"¥{summary['total_extra_cost']:,.0f}"
    )


@app.callback(
    Output('alert-material-filter', 'options'),
    [Input('alerts-data', 'data')]
)
def update_alert_material_filter(alerts):
    if not alerts:
        return []
    materials = sorted(list(set(a['material'] for a in alerts)))
    return [{'label': m, 'value': m} for m in materials]


def filter_alerts(alerts, materials, levels, statuses, start_date, end_date):
    filtered = alerts.copy()
    
    if materials:
        filtered = [a for a in filtered if a['material'] in materials]
    
    if levels:
        filtered = [a for a in filtered if a['level'] in levels]
    
    if statuses:
        filtered = [a for a in filtered if a['status'] in statuses]
    
    if start_date:
        start_date_str = start_date.strftime('%Y-%m-%d')
        filtered = [a for a in filtered if a['end_date'] >= start_date_str]
    
    if end_date:
        end_date_str = end_date.strftime('%Y-%m-%d')
        filtered = [a for a in filtered if a['start_date'] <= end_date_str]
    
    return filtered


@app.callback(
    Output('alerts-table-container', 'children'),
    [Input('alerts-data', 'data'),
     Input('alert-material-filter', 'value'),
     Input('alert-level-filter', 'value'),
     Input('alert-status-filter', 'value'),
     Input('alert-date-range', 'start_date'),
     Input('alert-date-range', 'end_date')]
)
def update_alerts_table(alerts, materials, levels, statuses, start_date, end_date):
    if not alerts:
        return html.Div("暂无预警数据", className="text-center text-muted py-4")
    
    filtered = filter_alerts(alerts, materials, levels, statuses, start_date, end_date)
    
    if not filtered:
        return html.Div("没有符合条件的预警", className="text-center text-muted py-4")
    
    table_data = []
    for alert in filtered:
        level_color_map = {'高': '#dc3545', '中': '#ffc107', '低': '#17a2b8'}
        status_color_map = {'待处理': '#6c757d', '已确认': '#007bff', '已处理': '#28a745'}
        
        table_data.append({
            '预警等级': alert['level'],
            '预警类型': alert['type'],
            '材料名称': alert['material'],
            '规格': alert['spec'],
            '开始日期': alert['start_date'],
            '结束日期': alert['end_date'],
            '平均损耗率%': f"{alert['avg_loss_pct']}%",
            '额外成本(元)': f"{alert['extra_cost']:,.2f}",
            '状态': alert['status'],
            '创建时间': alert['created_at'],
            'id': alert['id']
        })
    
    return html.Div([
        html.Small("💡 点击表格任意行查看详情并处理", className="text-muted mb-2 d-block"),
        dash_table.DataTable(
            id='alerts-table',
            data=table_data,
            columns=[
                {'name': '预警等级', 'id': '预警等级'},
                {'name': '预警类型', 'id': '预警类型'},
                {'name': '材料名称', 'id': '材料名称'},
                {'name': '规格', 'id': '规格'},
                {'name': '开始日期', 'id': '开始日期'},
                {'name': '结束日期', 'id': '结束日期'},
                {'name': '平均损耗率%', 'id': '平均损耗率%'},
                {'name': '额外成本(元)', 'id': '额外成本(元)'},
                {'name': '状态', 'id': '状态'},
                {'name': '创建时间', 'id': '创建时间'},
            ],
            page_size=10,
            style_table={'overflowX': 'auto'},
            style_header={'backgroundColor': 'rgb(230, 230, 230)', 'fontWeight': 'bold'},
            style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto'},
            style_data_conditional=[
                {'if': {'filter_query': '{预警等级} eq "高"', 'column_id': '预警等级'},
                 'backgroundColor': '#ffebee', 'color': '#c62828', 'fontWeight': 'bold'},
                {'if': {'filter_query': '{预警等级} eq "中"', 'column_id': '预警等级'},
                 'backgroundColor': '#fff3e0', 'color': '#e65100', 'fontWeight': 'bold'},
                {'if': {'filter_query': '{预警等级} eq "低"', 'column_id': '预警等级'},
                 'backgroundColor': '#e1f5fe', 'color': '#01579b', 'fontWeight': 'bold'},
                {'if': {'filter_query': '{状态} eq "待处理"', 'column_id': '状态'},
                 'backgroundColor': '#f5f5f5', 'color': '#616161'},
                {'if': {'filter_query': '{状态} eq "已确认"', 'column_id': '状态'},
                 'backgroundColor': '#e3f2fd', 'color': '#1565c0'},
                {'if': {'filter_query': '{状态} eq "已处理"', 'column_id': '状态'},
                 'backgroundColor': '#e8f5e9', 'color': '#2e7d32'},
            ],
            active_cell=None
        )
    ])


def render_alert_detail(alert):
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.H6("基本信息"),
                html.Hr(),
                dbc.Row([
                    dbc.Col([html.Strong("预警等级："), get_level_badge(alert['level'])], md=4),
                    dbc.Col([html.Strong("预警类型："), alert['type']], md=4),
                    dbc.Col([html.Strong("处理状态："), get_status_badge(alert['status'])], md=4),
                ]),
                dbc.Row([
                    dbc.Col([html.Strong("材料名称："), alert['material']], md=4),
                    dbc.Col([html.Strong("规格："), alert['spec']], md=4),
                    dbc.Col([html.Strong("单位："), alert['unit']], md=4),
                ], className='mt-2'),
                dbc.Row([
                    dbc.Col([html.Strong("开始日期："), alert['start_date']], md=4),
                    dbc.Col([html.Strong("结束日期："), alert['end_date']], md=4),
                    dbc.Col([html.Strong("创建时间："), alert['created_at']], md=4),
                ], className='mt-2'),
                dbc.Row([
                    dbc.Col([html.Strong("平均损耗率："), f"{alert['avg_loss_pct']}%"], md=4),
                    dbc.Col([html.Strong("涉及额外成本："), f"¥{alert['extra_cost']:,.2f}"], md=8),
                ], className='mt-2'),
                dbc.Row([
                    dbc.Col([html.Strong("预警描述："), html.P(alert['description'], className='mt-1')], md=12),
                ], className='mt-2'),
            ], width=12)
        ]),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                html.H6("资料员记录"),
                dbc.Textarea(
                    id='clerk-note-input',
                    placeholder='请补充异常原因与现场说明...',
                    value=alert.get('clerk_note', ''),
                    rows=3,
                    className='mb-2'
                ),
                dbc.Button('保存说明', id='save-clerk-note-btn', color='primary', size='sm')
            ], width=12)
        ]),
        html.Hr(),
        dbc.Row([
            dbc.Col([
                html.H6("项目主管处置"),
                dbc.Row([
                    dbc.Col([
                        html.Label("处理状态"),
                        dcc.Dropdown(
                            id='supervisor-status-dropdown',
                            options=[
                                {'label': '待处理', 'value': '待处理'},
                                {'label': '已确认', 'value': '已确认'},
                                {'label': '已处理', 'value': '已处理'}
                            ],
                            value=alert.get('status', '待处理')
                        )
                    ], md=4),
                ]),
                dbc.Textarea(
                    id='supervisor-comment-input',
                    placeholder='请填写处置意见...',
                    value=alert.get('supervisor_comment', ''),
                    rows=3,
                    className='mt-2 mb-2'
                ),
                dbc.Button('保存处置', id='save-supervisor-btn', color='success', size='sm'),
                html.Small(f"处理人：{alert.get('handled_by', '')} 处理时间：{alert.get('handled_at', '')}",
                          className='text-muted ms-2')
            ], width=12)
        ])
    ])


@app.callback(
    Output('alerts-data', 'data', allow_duplicate=True),
    [Input('save-clerk-note-btn', 'n_clicks')],
    [State('selected-alert-id', 'data'),
     State('clerk-note-input', 'value'),
     State('alerts-data', 'data')],
    prevent_initial_call=True
)
def save_clerk_note(n_clicks, alert_id, note, current_alerts):
    if n_clicks and alert_id:
        return processor.update_alert_clerk_note(alert_id, note)
    return dash.no_update


@app.callback(
    Output('alerts-data', 'data', allow_duplicate=True),
    [Input('save-supervisor-btn', 'n_clicks')],
    [State('selected-alert-id', 'data'),
     State('supervisor-status-dropdown', 'value'),
     State('supervisor-comment-input', 'value'),
     State('alerts-data', 'data')],
    prevent_initial_call=True
)
def save_supervisor_comment(n_clicks, alert_id, status, comment, current_alerts):
    if n_clicks and alert_id:
        return processor.update_alert_supervisor(alert_id, status, comment)
    return dash.no_update


@app.callback(
    [Output('alert-material-filter', 'value', allow_duplicate=True),
     Output('alert-level-filter', 'value'),
     Output('alert-status-filter', 'value'),
     Output('alert-date-range', 'start_date'),
     Output('alert-date-range', 'end_date')],
    [Input('reset-alert-filter', 'n_clicks')],
    prevent_initial_call=True
)
def reset_alert_filters(n_clicks):
    return None, None, None, None, None


@app.callback(
    [Output('cost-alert-summary', 'children'),
     Output('risk-chart', 'figure')],
    [Input('alerts-data', 'data')]
)
def update_cost_alert_section(alerts):
    if not alerts:
        return html.Div("暂无预警数据"), {}
    
    summary = processor.get_alert_summary(alerts)
    top_risks = processor.get_top_risk_materials(alerts)
    
    pending_cost = sum(a['extra_cost'] for a in alerts if a['status'] in ['待处理', '已确认'])
    resolved_cost = sum(a['extra_cost'] for a in alerts if a['status'] == '已处理')
    
    alert_summary_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("预警总数", className="card-title"),
            html.H3(summary['total'], className="text-primary")
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("未处理预警", className="card-title"),
            html.H3(summary['pending'] + summary['confirmed'], className="text-danger")
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("已处理预警", className="card-title"),
            html.H3(summary['resolved'], className="text-success")
        ])), md=2),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("未处理涉及成本", className="card-title"),
            html.H3(f"¥{pending_cost:,.0f}", className="text-warning")
        ])), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.H5("已处理涉及成本", className="card-title"),
            html.H3(f"¥{resolved_cost:,.0f}", className="text-info")
        ])), md=3),
    ])
    
    risk_fig = go.Figure()
    if not top_risks.empty:
        risk_fig.add_trace(go.Bar(
            x=top_risks['material'],
            y=top_risks['extra_cost'],
            name='额外成本(元)',
            marker_color='#d62728',
            text=top_risks['extra_cost'].apply(lambda x: f'¥{x:,.0f}'),
            textposition='auto'
        ))
        risk_fig.add_trace(go.Scatter(
            x=top_risks['material'],
            y=top_risks['high_count'],
            name='高风险预警数',
            yaxis='y2',
            mode='lines+markers',
            line=dict(color='#ff7f0e', width=3),
            marker=dict(size=10)
        ))
        risk_fig.update_layout(
            title='重点材料风险排行 (TOP 5)',
            xaxis_title='材料名称',
            yaxis_title='额外成本 (元)',
            yaxis2=dict(title='高风险预警数', overlaying='y', side='right'),
            height=400,
            legend=dict(orientation='h', y=-0.2)
        )
    
    return alert_summary_cards, risk_fig


@app.callback(
    [Output('alert-modal', 'is_open'),
     Output('alert-modal-title', 'children'),
     Output('alert-modal-content', 'children'),
     Output('selected-alert-id', 'data')],
    [Input('close-alert-modal', 'n_clicks'),
     Input('alerts-table', 'active_cell')],
    [State('alerts-table', 'data'),
     State('alerts-data', 'data'),
     State('alert-modal', 'is_open')]
)
def toggle_alert_modal(close_clicks, active_cell, table_data, alerts, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "", "", ""
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == 'close-alert-modal':
        return False, "", "", ""
    
    if trigger_id == 'alerts-table' and active_cell and table_data and alerts:
        row_idx = active_cell['row']
        if row_idx < len(table_data):
            alert_id = table_data[row_idx].get('id')
            if alert_id:
                alert = next((a for a in alerts if a['id'] == alert_id), None)
                if alert:
                    content = render_alert_detail(alert)
                    title = f"预警详情 - {alert['material']}"
                    return True, title, content, alert_id
    
    return dash.no_update


if __name__ == '__main__':
    app.run(debug=False, port=8051)
